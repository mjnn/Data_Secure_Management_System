<template>
  <div class="slb" :class="{ 'slb--nested': nested }">
    <div v-if="nested" class="slb__group-bar dsms-glass-panel">
      <span class="slb__paren" aria-hidden="true">(</span>
      <dsms-filterable-select v-model="group.op" class="slb__op-select" aria-label="组内逻辑">
        <el-option v-for="op in logicOperators" :key="op.value" :label="op.label" :value="op.value" />
      </dsms-filterable-select>
      <el-button link type="danger" @click="emit('remove')">删除分组</el-button>
      <span class="slb__paren slb__paren--end" aria-hidden="true">)</span>
    </div>
    <div v-else class="slb__root-op">
      <span class="slb__root-op-label">触发条件逻辑</span>
      <dsms-filterable-select v-model="group.op" class="slb__op-select" aria-label="顶层逻辑">
        <el-option v-for="op in logicOperators" :key="op.value" :label="op.label" :value="op.value" />
      </dsms-filterable-select>
    </div>

    <p v-if="!nested" class="slb__hint">
      每条条件先选类型：<strong>密级</strong>（下拉）、<strong>分类</strong>（树形下拉）、<strong>生命周期字段</strong>（先选字段名再选值）。对具体数据字段求值在页面下方操作。
    </p>

    <div class="slb__children">
      <template v-for="(child, idx) in group.children" :key="child.id">
        <p v-if="idx > 0" class="slb__between">{{ group.op === "OR" ? "或" : "且" }}</p>

        <SecurityTriggerConditionRow
          v-if="child.type === 'condition'"
          :cond="child"
          :index="idx + 1"
          :removable="group.children.length > 1"
          @remove="removeChild(idx)"
        />

        <SecurityLogicExprBuilder
          v-else-if="child.type === 'group'"
          :group="child"
          nested
          @remove="removeChild(idx)"
        />
      </template>
    </div>

    <div class="slb__actions">
      <el-button @click="addCondition">添加条件</el-button>
      <el-button @click="addGroup">添加括号分组</el-button>
    </div>
  </div>
</template>

<script setup>
import DsmsFilterableSelect from "../DsmsFilterableSelect.vue";
import SecurityTriggerConditionRow from "./SecurityTriggerConditionRow.vue";
import {
  SECURITY_LOGIC_OPERATORS,
  newTriggerConditionNode,
  newTriggerGroupNode
} from "../../data/securityLogicTree.js";

defineOptions({ name: "SecurityLogicExprBuilder" });

const props = defineProps({
  group: { type: Object, required: true },
  nested: { type: Boolean, default: false }
});

const emit = defineEmits(["remove"]);

const logicOperators = SECURITY_LOGIC_OPERATORS;

function addCondition() {
  props.group.children.push(newTriggerConditionNode());
}

function addGroup() {
  props.group.children.push(newTriggerGroupNode());
}

function removeChild(idx) {
  props.group.children.splice(idx, 1);
  if (!props.group.children.length) {
    props.group.children.push(newTriggerConditionNode());
  }
}
</script>

<style scoped>
.slb {
  margin-bottom: 8px;
}

.slb--nested {
  margin: 12px 0 12px 1rem;
  padding-left: 12px;
  border-left: 2px solid var(--el-border-color-lighter, #e4e7ed);
}

.slb__group-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
}

.slb__paren {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text-secondary);
}

.slb__root-op {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.slb__root-op-label {
  font-size: 0.875rem;
  color: var(--dsms-text-secondary);
}

.slb__hint {
  margin: 0 0 12px;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--dsms-text-secondary);
}

.slb__op-select {
  width: 140px;
}

.slb__children {
  margin-bottom: 8px;
}

.slb__between {
  margin: 4px 0 4px 2rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--el-color-primary);
}

.slb__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
</style>
