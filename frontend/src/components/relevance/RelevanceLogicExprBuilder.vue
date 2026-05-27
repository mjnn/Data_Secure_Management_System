<template>
  <div class="rlb" :class="{ 'rlb--nested': nested }">
    <div v-if="nested" class="rlb__group-bar dsms-glass-panel">
      <span class="rlb__paren" aria-hidden="true">(</span>
      <dsms-filterable-select v-model="group.op" class="rlb__op-select" aria-label="组内逻辑">
        <el-option v-for="op in logicOperators" :key="op.value" :label="op.label" :value="op.value" />
      </dsms-filterable-select>
      <el-button link type="danger" @click="emit('remove')">删除分组</el-button>
      <span class="rlb__paren rlb__paren--end" aria-hidden="true">)</span>
    </div>
    <div v-else class="rlb__root-op">
      <span class="rlb__root-op-label">表达式逻辑</span>
      <dsms-filterable-select v-model="group.op" class="rlb__op-select" aria-label="顶层逻辑">
        <el-option v-for="op in logicOperators" :key="op.value" :label="op.label" :value="op.value" />
      </dsms-filterable-select>
    </div>

    <p v-if="!nested" class="rlb__hint">
      每条谓词为<strong>问题</strong>（下拉）+ <strong>答案</strong>（下拉）；支持添加条件与括号分组，组合方式与安全要求触发条件一致。
    </p>

    <div class="rlb__children">
      <template v-for="(child, idx) in group.children" :key="child.id">
        <p v-if="idx > 0" class="rlb__between">{{ group.op === "OR" ? "或" : "且" }}</p>

        <RelevanceConditionRow
          v-if="child.type === 'condition'"
          :cond="child"
          :index="idx + 1"
          :removable="group.children.length > 1"
          @remove="removeChild(idx)"
        />

        <RelevanceLogicExprBuilder
          v-else-if="child.type === 'group'"
          :group="child"
          nested
          @remove="removeChild(idx)"
        />
      </template>
    </div>

    <div class="rlb__actions">
      <el-button @click="addCondition">添加谓词</el-button>
      <el-button @click="addGroup">添加括号分组</el-button>
    </div>
  </div>
</template>

<script setup>
import DsmsFilterableSelect from "../DsmsFilterableSelect.vue";
import RelevanceConditionRow from "./RelevanceConditionRow.vue";
import {
  RELEVANCE_LOGIC_OPERATORS,
  newRelevanceConditionNode,
  newRelevanceGroupNode
} from "../../data/relevanceLogicTree.js";

defineOptions({ name: "RelevanceLogicExprBuilder" });

const props = defineProps({
  group: { type: Object, required: true },
  nested: { type: Boolean, default: false }
});

const emit = defineEmits(["remove"]);

const logicOperators = RELEVANCE_LOGIC_OPERATORS;

function addCondition() {
  props.group.children.push(newRelevanceConditionNode());
}

function addGroup() {
  props.group.children.push(newRelevanceGroupNode());
}

function removeChild(idx) {
  props.group.children.splice(idx, 1);
  if (!props.group.children.length) {
    props.group.children.push(newRelevanceConditionNode());
  }
}
</script>

<style scoped>
.rlb {
  margin-bottom: 8px;
}

.rlb--nested {
  margin: 12px 0 12px 1rem;
  padding-left: 12px;
  border-left: 2px solid var(--el-border-color-lighter, #e4e7ed);
}

.rlb__group-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
}

.rlb__paren {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text-secondary);
}

.rlb__root-op {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.rlb__root-op-label {
  font-size: 0.875rem;
  color: var(--dsms-text-secondary);
}

.rlb__hint {
  margin: 0 0 12px;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--dsms-text-secondary);
}

.rlb__op-select {
  width: 140px;
}

.rlb__children {
  margin-bottom: 8px;
}

.rlb__between {
  margin: 4px 0 4px 2rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--el-color-primary);
}

.rlb__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
</style>
