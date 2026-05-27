<template>
  <div class="rcr">
    <span v-if="showIndex" class="rcr__index">{{ index }}</span>

    <span class="rcr__label">问题</span>
    <dsms-filterable-select
      v-model="cond.questionId"
      class="rcr__question"
      placeholder="选择问题"
      aria-label="问题"
      @change="onQuestionChange"
    >
      <el-option v-for="q in questionOptions" :key="q.id" :label="q.title" :value="q.id" />
    </dsms-filterable-select>

    <span class="rcr__label">答案</span>
    <dsms-filterable-select
      v-model="cond.answerId"
      class="rcr__answer"
      placeholder="选择答案"
      aria-label="答案"
      :disabled="!cond.questionId"
      @change="sync"
    >
      <el-option v-for="a in answerOptions" :key="a.id" :label="a.label" :value="a.id" />
    </dsms-filterable-select>

    <el-button v-if="removable" link type="danger" @click="emit('remove')">删除</el-button>
  </div>
</template>

<script setup>
import { computed } from "vue";
import DsmsFilterableSelect from "../DsmsFilterableSelect.vue";
import {
  listRelevanceAnswerOptions,
  listRelevanceQuestionOptions,
  syncRelevanceConditionValueKey
} from "../../data/relevanceConditionCatalog.js";

const props = defineProps({
  cond: { type: Object, required: true },
  index: { type: Number, default: 1 },
  showIndex: { type: Boolean, default: true },
  removable: { type: Boolean, default: true }
});

const emit = defineEmits(["remove"]);

const questionOptions = listRelevanceQuestionOptions();

const answerOptions = computed(() => listRelevanceAnswerOptions(props.cond.questionId));

function sync() {
  syncRelevanceConditionValueKey(props.cond);
}

function onQuestionChange() {
  props.cond.answerId = "";
  sync();
}
</script>

<style scoped>
.rcr {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.rcr__index {
  flex: 0 0 1.5rem;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
  text-align: right;
}

.rcr__label {
  flex: 0 0 auto;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.rcr__question {
  flex: 1 1 200px;
  min-width: 160px;
  max-width: 280px;
}

.rcr__answer {
  flex: 1 1 140px;
  min-width: 120px;
  max-width: 200px;
}
</style>
