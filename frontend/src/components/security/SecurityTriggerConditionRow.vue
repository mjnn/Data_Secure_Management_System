<template>
  <div class="stc">
    <span v-if="showIndex" class="stc__index">{{ index }}</span>

    <dsms-filterable-select
      v-model="cond.attributeKind"
      class="stc__kind"
      aria-label="条件类型"
      @change="onKindChange"
    >
      <el-option v-for="k in attrOptions" :key="k.value" :label="k.label" :value="k.value" />
    </dsms-filterable-select>

    <template v-if="cond.attributeKind === CONDITION_ATTR_GRADE">
      <span class="stc__label">密级</span>
      <dsms-filterable-select
        v-model="cond.gradeValue"
        class="stc__value"
        placeholder="选择密级"
        aria-label="密级"
        @change="sync"
      >
        <el-option v-for="g in gradeOptions" :key="g" :label="g" :value="g" />
      </dsms-filterable-select>
    </template>

    <template v-else-if="cond.attributeKind === CONDITION_ATTR_TAXONOMY">
      <span class="stc__label">分类</span>
      <el-tree-select
        v-model="cond.taxonomyPathStored"
        class="stc__tree"
        :data="taxonomyTreeData"
        check-strictly
        filterable
        :render-after-expand="false"
        placeholder="选择分类树节点"
        aria-label="分类"
        :props="treeProps"
        @change="sync"
      />
    </template>

    <template v-else-if="cond.attributeKind === CONDITION_ATTR_LIFECYCLE">
      <span class="stc__label">生命周期字段</span>
      <dsms-filterable-select
        v-model="cond.lifecycleFieldKey"
        class="stc__lc-field"
        placeholder="选择字段名"
        aria-label="生命周期字段名"
        @change="onLifecycleFieldChange"
      >
        <el-option v-for="f in lifecycleFields" :key="f.field_key" :label="f.label" :value="f.field_key" />
      </dsms-filterable-select>
      <dsms-filterable-select
        v-model="cond.lifecycleValue"
        class="stc__value"
        placeholder="选择取值"
        aria-label="生命周期字段取值"
        :disabled="!cond.lifecycleFieldKey"
        @change="sync"
      >
        <el-option v-for="v in lifecycleValues" :key="v" :label="v" :value="v" />
      </dsms-filterable-select>
    </template>

    <el-button v-if="removable" link type="danger" @click="emit('remove')">删除</el-button>
  </div>
</template>

<script setup>
import { computed } from "vue";
import DsmsFilterableSelect from "../DsmsFilterableSelect.vue";
import {
  CONDITION_ATTR_GRADE,
  CONDITION_ATTR_LIFECYCLE,
  CONDITION_ATTR_OPTIONS,
  CONDITION_ATTR_TAXONOMY,
  buildTaxonomyTreeSelectData,
  listGradeOptions,
  listLifecycleMetaFields,
  listLifecycleValuesForMetaField,
  syncConditionValueKey
} from "../../data/securityConditionCatalog.js";

const props = defineProps({
  cond: { type: Object, required: true },
  index: { type: Number, default: 1 },
  showIndex: { type: Boolean, default: true },
  removable: { type: Boolean, default: true }
});

const emit = defineEmits(["remove"]);

const attrOptions = CONDITION_ATTR_OPTIONS;
const treeProps = { value: "value", label: "label", children: "children" };
const gradeOptions = listGradeOptions();
const taxonomyTreeData = buildTaxonomyTreeSelectData();
const lifecycleFields = listLifecycleMetaFields();

const lifecycleValues = computed(() => listLifecycleValuesForMetaField(props.cond.lifecycleFieldKey));

function sync() {
  syncConditionValueKey(props.cond);
}

function onKindChange() {
  props.cond.gradeValue = "";
  props.cond.taxonomyPathStored = "";
  props.cond.lifecycleFieldKey = "";
  props.cond.lifecycleValue = "";
  sync();
}

function onLifecycleFieldChange() {
  props.cond.lifecycleValue = "";
  sync();
}
</script>

<style scoped>
.stc {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.stc__index {
  flex: 0 0 1.5rem;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
  text-align: right;
}

.stc__kind {
  width: 132px;
  flex: 0 0 auto;
}

.stc__label {
  flex: 0 0 auto;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.stc__value {
  flex: 1 1 160px;
  min-width: 140px;
  max-width: 220px;
}

.stc__tree {
  flex: 1 1 240px;
  min-width: 200px;
  max-width: 360px;
}

.stc__lc-field {
  flex: 1 1 160px;
  min-width: 140px;
  max-width: 200px;
}
</style>
