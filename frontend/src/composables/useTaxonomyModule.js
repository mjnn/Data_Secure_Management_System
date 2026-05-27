/**
 * 分类树模块（层级 + 节点 + 数据字段分类）共享状态与步骤定义。
 */

import { computed, onBeforeUnmount, onMounted, ref, unref } from "vue";
import { loadFieldCatalogWithTaxonomy, DATA_FIELD_CATALOG_PERSIST_EVENT } from "../data/fieldTaxonomyClassificationMock.js";
import { loadTaxonomyLevels, TAXONOMY_LEVEL_PERSIST_EVENT } from "../data/taxonomyLevelMock.js";
import { loadTaxonomyNodes, TAXONOMY_NODE_PERSIST_EVENT } from "../data/taxonomyNodeMock.js";

export const TAXONOMY_MODULE_STEPS = [
  {
    key: "levels",
    title: "分类树层级",
    routeName: "dashboard-rule-taxonomy-levels",
    description: "0、1、2… 级定义"
  },
  {
    key: "nodes",
    title: "分类树节点",
    routeName: "dashboard-rule-taxonomy-nodes",
    description: "code / 名称 / 上下级"
  },
  {
    key: "fieldClassification",
    title: "数据字段分类",
    routeName: "dashboard-rule-taxonomy-field-classification",
    description: "字段 taxonomy_code"
  },
  {
    key: "classificationConfig",
    title: "矩阵与规则",
    routeName: "dashboard-rule-taxonomy-classification-config",
    description: "分类矩阵 / 规则"
  },
  {
    key: "classificationResults",
    title: "自动分类结果",
    routeName: "dashboard-rule-taxonomy-classification-results",
    description: "规则/矩阵求值"
  }
];

export function taxonomyStepIndexForKey(stepKey) {
  const i = TAXONOMY_MODULE_STEPS.findIndex((s) => s.key === stepKey);
  return i >= 0 ? i : 0;
}

function readModuleSnapshot() {
  const levels = loadTaxonomyLevels();
  const nodes = loadTaxonomyNodes();
  const fields = loadFieldCatalogWithTaxonomy();
  const classified = fields.filter((f) => String(f.taxonomy_code || "").trim()).length;
  return {
    levelCount: levels.length,
    nodeCount: nodes.length,
    fieldCount: fields.length,
    classifiedFieldCount: classified
  };
}

/** @param {import('vue').MaybeRefOrGetter<'levels' | 'nodes' | 'fieldClassification' | 'classificationResults'>} pageKey */
export function useTaxonomyModule(pageKey) {
  const tick = ref(0);
  const activeStepIndex = computed(() => taxonomyStepIndexForKey(unref(pageKey)));

  const snapshot = computed(() => {
    void tick.value;
    return readModuleSnapshot();
  });

  const moduleHints = computed(() => {
    const currentPage = unref(pageKey);
    const s = snapshot.value;
    const hints = [];
    if (s.levelCount === 0) {
      hints.push({
        type: "warning",
        title: "请先配置分类树层级",
        description: "尚无层级定义，请在本模块第一步新增 0（根级）及 1、2、3… 级。"
      });
      return hints;
    }
    if (s.nodeCount === 0) {
      hints.push({
        type: "warning",
        title: "请维护分类树节点",
        description: "层级已就绪，请在「分类树节点」中新增根节点并逐级展开子节点。"
      });
    }
    if (currentPage === "nodes" && s.levelCount > 0 && s.nodeCount > 0) {
      hints.push({
        type: "info",
        title: "节点深度须与层级定义一致",
        description: "子节点深度不得超过「分类树层级」中已注册的最大分类级。"
      });
    }
    if (currentPage === "fieldClassification") {
      if (s.nodeCount === 0) {
        hints.push({
          type: "warning",
          title: "请先配置分类树节点",
          description: "为数据字段指定分类前，需有可用的分类节点。"
        });
      } else if (s.fieldCount > 0 && s.classifiedFieldCount < s.fieldCount) {
        hints.push({
          type: "info",
          title: "尚有未分类的数据字段",
          description: `已分类 ${s.classifiedFieldCount} / ${s.fieldCount} 个字段，可在下方表单继续配置。`
        });
      }
    }
    if (currentPage === "classificationConfig") {
      hints.push({
        type: "info",
        title: "配置完成后请重算",
        description: "矩阵与规则保存后，请在「自动分类结果」执行全量重算以生成结果。"
      });
    }
    return hints;
  });

  const statusSummary = computed(() => {
    const s = snapshot.value;
    return `层级 ${s.levelCount} · 节点 ${s.nodeCount} · 已分类字段 ${s.classifiedFieldCount}/${s.fieldCount}`;
  });

  function refresh() {
    tick.value++;
  }

  function onPersist() {
    refresh();
  }

  onMounted(() => {
    refresh();
    window.addEventListener(TAXONOMY_LEVEL_PERSIST_EVENT, onPersist);
    window.addEventListener(TAXONOMY_NODE_PERSIST_EVENT, onPersist);
    window.addEventListener(DATA_FIELD_CATALOG_PERSIST_EVENT, onPersist);
  });

  onBeforeUnmount(() => {
    window.removeEventListener(TAXONOMY_LEVEL_PERSIST_EVENT, onPersist);
    window.removeEventListener(TAXONOMY_NODE_PERSIST_EVENT, onPersist);
    window.removeEventListener(DATA_FIELD_CATALOG_PERSIST_EVENT, onPersist);
  });

  return {
    activeStepIndex,
    snapshot,
    moduleHints,
    statusSummary,
    refresh,
    steps: TAXONOMY_MODULE_STEPS
  };
}
