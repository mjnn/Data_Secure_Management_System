/**
 * 相关性判断模块（问卷 + 表达式）共享状态与步骤定义。
 */

import { computed, onBeforeUnmount, onMounted, ref, unref } from "vue";
import { loadRelevanceExpression, validateExpressionPayload } from "../data/relevanceExpressionMock.js";
import {
  loadRelevanceQuestionnaireQuestions,
  RELEVANCE_QUESTIONNAIRE_PERSIST_EVENT
} from "../data/relevanceQuestionnaireMock.js";
import { RELEVANCE_EXPRESSION_PERSIST_EVENT } from "../data/relevanceExpressionMock.js";
import { PORTAL_DATA_REFRESH_EVENT } from "../api/portalApi.js";
import { collectRelevanceConditions } from "../data/relevanceLogicTree.js";

export const RELEVANCE_STANDARD_STEPS = [
  {
    key: "questionnaire",
    title: "相关性问卷",
    routeName: "dashboard-rule-relevance-questionnaire",
    description: "维护题目与选项"
  },
  {
    key: "expression",
    title: "表达式配置和验证",
    routeName: "dashboard-rule-relevance-standard-expression",
    description: "问题×答案谓词与试算"
  }
];

export function stepIndexForKey(stepKey) {
  const i = RELEVANCE_STANDARD_STEPS.findIndex((s) => s.key === stepKey);
  return i >= 0 ? i : 0;
}

function readModuleSnapshot() {
  const questions = loadRelevanceQuestionnaireQuestions();
  const expr = loadRelevanceExpression();
  const exprValid = validateExpressionPayload(expr).ok;
  const conditionCount = collectRelevanceConditions(expr.logic_root).length;
  return {
    questionCount: questions.length,
    conditionCount,
    expressionValid: exprValid,
    expressionUpdatedAt: expr.updatedAt || ""
  };
}

/** @param {import('vue').MaybeRefOrGetter<'questionnaire' | 'expression'>} pageKey */
export function useRelevanceStandardModule(pageKey) {
  const tick = ref(0);
  const activeStepIndex = computed(() => stepIndexForKey(unref(pageKey)));

  const snapshot = computed(() => {
    void tick.value;
    return readModuleSnapshot();
  });

  const moduleHints = computed(() => {
    const currentPage = unref(pageKey);
    const s = snapshot.value;
    const hints = [];
    if (s.questionCount === 0) {
      hints.push({
        type: "warning",
        title: "请先配置相关性问卷",
        description: "尚无问卷题目，请先在步骤 1「相关性问卷」中新增题目与选项。"
      });
      return hints;
    }
    if (currentPage === "questionnaire" && s.questionCount > 0) {
      hints.push({
        type: "info",
        title: "问卷已就绪",
        description: "可进入「表达式配置和验证」，用问题与答案下拉配置谓词并组合逻辑。"
      });
    }
    if (currentPage === "expression" && s.questionCount === 0) {
      hints.push({
        type: "warning",
        title: "请先配置问卷",
        description: "表达式中的问题与答案来自问卷，请先完成步骤 1。"
      });
    } else if (currentPage === "expression" && !s.expressionValid) {
      hints.push({
        type: "info",
        title: "请完善并保存表达式",
        description: "为每条谓词选择问题与答案并保存后，可在下方功能 FO 填报表中提交试算相关性。"
      });
    } else if (currentPage === "expression" && s.expressionValid) {
      hints.push({
        type: "info",
        title: "可试算相关性",
        description: "在下方按功能 FO 视角填写问卷并点击「提交并判定相关性」。"
      });
    }
    return hints;
  });

  const statusSummary = computed(() => {
    const s = snapshot.value;
    return `问卷 ${s.questionCount} 题 · 谓词 ${s.conditionCount} 条${s.expressionValid ? " · 表达式已配置" : ""}`;
  });

  function refresh() {
    tick.value++;
  }

  function onPersist() {
    refresh();
  }

  onMounted(() => {
    refresh();
    window.addEventListener(RELEVANCE_QUESTIONNAIRE_PERSIST_EVENT, onPersist);
    window.addEventListener(RELEVANCE_EXPRESSION_PERSIST_EVENT, onPersist);
    window.addEventListener(PORTAL_DATA_REFRESH_EVENT, onPersist);
  });

  onBeforeUnmount(() => {
    window.removeEventListener(RELEVANCE_QUESTIONNAIRE_PERSIST_EVENT, onPersist);
    window.removeEventListener(RELEVANCE_EXPRESSION_PERSIST_EVENT, onPersist);
    window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, onPersist);
  });

  return {
    activeStepIndex,
    snapshot,
    moduleHints,
    statusSummary,
    refresh,
    steps: RELEVANCE_STANDARD_STEPS
  };
}
