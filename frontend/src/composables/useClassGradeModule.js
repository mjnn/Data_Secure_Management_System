/**
 * 密级绑定模块（密级定义 + 数据字段绑定）共享状态与步骤。
 */

import { computed, onBeforeUnmount, onMounted, ref, unref } from "vue";
import { countFieldBindingsByGradeLabel, loadFieldClassGradeBindings, FIELD_CLASS_GRADE_PERSIST_EVENT } from "../data/fieldClassGradeBindingMock.js";
import {
  loadSensitivityLevels,
  SENSITIVITY_LEVEL_PERSIST_EVENT
} from "../data/sensitivityLevelMock.js";
import { loadDataFieldCatalogEntries, DATA_FIELD_CATALOG_PERSIST_EVENT } from "../data/dataFieldCatalogMock.js";

export const CLASS_GRADE_MODULE_STEPS = [
  {
    key: "levels",
    title: "密级定义",
    routeName: "dashboard-rule-classification-levels",
    description: "可绑定的密级标签"
  },
  {
    key: "bindings",
    title: "数据字段绑定",
    routeName: "dashboard-rule-classification-bindings",
    description: "字段 grade_label"
  }
];

export function classGradeStepIndexForKey(stepKey) {
  const i = CLASS_GRADE_MODULE_STEPS.findIndex((s) => s.key === stepKey);
  return i >= 0 ? i : 0;
}

function readModuleSnapshot() {
  const levels = loadSensitivityLevels();
  const bindings = loadFieldClassGradeBindings();
  const fields = loadDataFieldCatalogEntries();
  const bound = bindings.filter((b) => String(b.grade_label || "").trim()).length;
  return {
    levelCount: levels.length,
    fieldCount: fields.length,
    boundFieldCount: bound
  };
}

/** @param {import('vue').MaybeRefOrGetter<'levels' | 'bindings'>} pageKey */
export function useClassGradeModule(pageKey) {
  const tick = ref(0);
  const activeStepIndex = computed(() => classGradeStepIndexForKey(unref(pageKey)));

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
        title: "请先定义密级",
        description: "尚无密级定义，请在本模块第一步新增密级（如公开、内部、秘密、机密）。"
      });
      return hints;
    }
    if (currentPage === "levels" && s.levelCount > 0) {
      hints.push({
        type: "info",
        title: "密级已就绪",
        description: "可进入「数据字段绑定」为各数据字段指定密级（grade_label）。"
      });
    }
    if (currentPage === "bindings") {
      if (s.fieldCount === 0) {
        hints.push({
          type: "warning",
          title: "暂无数据字段",
          description: "请先在「数据字段」主数据页维护字段目录。"
        });
      } else if (s.boundFieldCount < s.fieldCount) {
        hints.push({
          type: "info",
          title: "尚有未绑定密级的数据字段",
          description: `已绑定 ${s.boundFieldCount} / ${s.fieldCount} 个字段。`
        });
      }
    }
    return hints;
  });

  const statusSummary = computed(() => {
    const s = snapshot.value;
    return `密级 ${s.levelCount} 种 · 已绑定字段 ${s.boundFieldCount}/${s.fieldCount}`;
  });

  function refresh() {
    tick.value++;
  }

  function onPersist() {
    refresh();
  }

  onMounted(() => {
    refresh();
    window.addEventListener(SENSITIVITY_LEVEL_PERSIST_EVENT, onPersist);
    window.addEventListener(FIELD_CLASS_GRADE_PERSIST_EVENT, onPersist);
    window.addEventListener(DATA_FIELD_CATALOG_PERSIST_EVENT, onPersist);
  });

  onBeforeUnmount(() => {
    window.removeEventListener(SENSITIVITY_LEVEL_PERSIST_EVENT, onPersist);
    window.removeEventListener(FIELD_CLASS_GRADE_PERSIST_EVENT, onPersist);
    window.removeEventListener(DATA_FIELD_CATALOG_PERSIST_EVENT, onPersist);
  });

  return {
    activeStepIndex,
    snapshot,
    moduleHints,
    statusSummary,
    refresh,
    steps: CLASS_GRADE_MODULE_STEPS,
    countFieldBindingsByGradeLabel
  };
}
