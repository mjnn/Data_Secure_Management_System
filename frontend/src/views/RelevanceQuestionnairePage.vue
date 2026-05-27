<template>
  <section class="rqp dsms-glass-panel dsms-animate-stagger-1" aria-labelledby="rqp-title">
    <header class="rqp__header">
      <h3 id="rqp-title" class="rqp__title">相关性问卷</h3>
      <p class="rqp__lead">
        制定业务功能与数据安全之间的<strong>相关性判断问卷</strong>（题干 + 选项）。数据来自后端
        <code class="rqp__code">/questionnaires/questions</code>。
      </p>
    </header>

    <div class="rqp__toolbar">
      <el-button type="primary" @click="openCreate">新增题目</el-button>
      <el-button type="primary" plain @click="goExpression">下一步：表达式配置</el-button>
    </div>

    <el-table
      class="rqp__table"
        :data="questionRowsDisplay"
        row-key="id"
        border
        stripe
        empty-text="暂无问卷题目，请点击「新增题目」"
      >
        <el-table-column type="expand" width="48">
          <template #default="{ row }">
            <div class="rqp__expand">
              <p class="rqp__expand-label">选项列表</p>
              <el-table :data="row.options" size="small" border>
                <el-table-column type="index" label="序号" width="64" :index="(i) => i + 1" />
                <el-table-column prop="label" label="选项文案" min-width="200" show-overflow-tooltip />
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column type="index" label="序号" width="64" :index="indexFromOne" />
        <el-table-column prop="title" label="题目" min-width="280" show-overflow-tooltip />
        <el-table-column prop="key" label="题目 Key" width="200" show-overflow-tooltip />
        <el-table-column label="选项数" width="88" align="center">
          <template #default="{ row }">
            {{ row.options?.length ?? 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新日期" width="120" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
  </section>

  <el-dialog
    v-model="editVisible"
    class="rqp-edit-dialog"
    :title="editMode === 'create' ? '新增题目' : '编辑题目'"
    width="560px"
    append-to-body
    align-center
    destroy-on-close
    @closed="resetEditForm"
  >
    <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="88px">
      <el-form-item label="题目" prop="title">
        <el-input
          v-model="editForm.title"
          type="textarea"
          :rows="2"
          maxlength="500"
          show-word-limit
          placeholder="请输入相关性判断题干"
          @blur="onTitleBlur"
        />
      </el-form-item>
      <el-form-item label="题目 Key" prop="key">
        <el-input v-model="editForm.key" maxlength="80" placeholder="小写蛇形，空间内唯一" />
      </el-form-item>
      <el-form-item label="选项" required>
        <div class="rqp__options-editor">
          <div v-for="(opt, idx) in editForm.options" :key="opt._uid" class="rqp__option-row">
            <span class="rqp__option-index">{{ idx + 1 }}</span>
            <el-input v-model="opt.label" maxlength="200" placeholder="选项文案" />
            <el-button
              link
              type="danger"
              :disabled="editForm.options.length <= 1"
              @click="removeOptionRow(idx)"
            >
              删除
            </el-button>
          </div>
          <el-button class="rqp__add-option" @click="addOptionRow">添加选项</el-button>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editVisible = false">取消</el-button>
      <el-button type="primary" @click="submitEdit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { ensurePortalTenantReady, usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import {
  createQuestionnaireQuestion,
  deleteQuestionnaireQuestions,
  fetchQuestionnaireQuestions,
  updateQuestionnaireQuestion
} from "../api/dsmsSpaceApi.js";
import { PORTAL_DATA_REFRESH_EVENT } from "../api/portalApi.js";
import {
  generateOptionId,
  suggestQuestionKey
} from "../data/relevanceQuestionnaireMock.js";

const router = useRouter();
const { tenantId, spaceId, ready } = usePortalTenantContext();
const questionRows = ref([]);
const loading = ref(false);

function goExpression() {
  router.push({ name: "dashboard-rule-relevance-standard-expression" });
}

const questionRowsDisplay = computed(() => questionRows.value);

function indexFromOne(index) {
  return index + 1;
}

async function loadQuestions() {
  if (!ready.value || !tenantId.value) return;
  loading.value = true;
  try {
    questionRows.value = await fetchQuestionnaireQuestions(tenantId.value, spaceId.value);
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载问卷失败");
  } finally {
    loading.value = false;
  }
}

const editVisible = ref(false);
const editMode = ref("create");
const editingId = ref("");
const editFormRef = ref(null);
const editForm = ref({
  title: "",
  key: "",
  options: [{ _uid: 1, id: "", label: "" }]
});

let optionUid = 2;

const editRules = {
  title: [{ required: true, message: "请输入题目", trigger: "blur" }],
  key: [
    { required: true, message: "请输入题目 Key", trigger: "blur" },
    {
      pattern: /^[a-z][a-z0-9_]*$/,
      message: "Key 须为小写蛇形（^[a-z][a-z0-9_]*$）",
      trigger: "blur"
    }
  ]
};

function emptyOptionRow() {
  return { _uid: optionUid++, id: "", label: "" };
}

function openCreate() {
  editMode.value = "create";
  editingId.value = "";
  editForm.value = {
    title: "",
    key: "",
    options: [emptyOptionRow(), emptyOptionRow()]
  };
  editVisible.value = true;
}

function openEdit(row) {
  editMode.value = "edit";
  editingId.value = row.id;
  editForm.value = {
    title: row.title || "",
    key: row.key || "",
    options: (row.options || []).map((o) => ({
      _uid: optionUid++,
      id: o.id,
      label: o.label || ""
    }))
  };
  if (!editForm.value.options.length) {
    editForm.value.options = [emptyOptionRow()];
  }
  editVisible.value = true;
}

function resetEditForm() {
  editFormRef.value?.clearValidate?.();
}

function onTitleBlur() {
  if (editMode.value === "create" && !String(editForm.value.key || "").trim()) {
    editForm.value.key = suggestQuestionKey(editForm.value.title);
  }
}

function addOptionRow() {
  editForm.value.options.push(emptyOptionRow());
}

function removeOptionRow(idx) {
  if (editForm.value.options.length <= 1) return;
  editForm.value.options.splice(idx, 1);
}

function validateOptions() {
  const labels = editForm.value.options.map((o) => String(o.label || "").trim()).filter(Boolean);
  if (!labels.length) {
    ElMessage.error("请至少配置一个选项。");
    return null;
  }
  const set = new Set(labels);
  if (set.size !== labels.length) {
    ElMessage.error("选项文案不能重复。");
    return null;
  }
  return editForm.value.options
    .map((o) => ({
      id: o.id || generateOptionId(),
      label: String(o.label || "").trim()
    }))
    .filter((o) => o.label);
}

async function submitEdit() {
  const form = editFormRef.value;
  if (!form) return;
  try {
    await form.validate();
  } catch {
    return;
  }
  const options = validateOptions();
  if (!options) return;

  if (editMode.value === "create") {
    try {
      await createQuestionnaireQuestion(tenantId.value, spaceId.value, {
        title: editForm.value.title,
        key: editForm.value.key,
        options,
        sort_order: questionRows.value.length
      });
      ElMessage.success("已新增题目");
      await loadQuestions();
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || "新增失败");
      return;
    }
  } else {
    const row = questionRows.value.find((q) => String(q.id) === String(editingId.value));
    try {
      await updateQuestionnaireQuestion(tenantId.value, spaceId.value, {
        _apiId: row?._apiId || Number(editingId.value),
        id: editingId.value,
        title: editForm.value.title,
        key: editForm.value.key,
        options,
        sort_order: row?.sort_order ?? 0
      });
      ElMessage.success("已保存");
      await loadQuestions();
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || "保存失败");
      return;
    }
  }
  editVisible.value = false;
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除题目「${row.title}」吗？`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }
  try {
    await deleteQuestionnaireQuestions(tenantId.value, spaceId.value, [row._apiId || row.id]);
    ElMessage.success("已删除");
    await loadQuestions();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "删除失败");
  }
}

onMounted(async () => {
  await ensurePortalTenantReady();
  await loadQuestions();
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, loadQuestions);
});

onBeforeUnmount(() => {
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, loadQuestions);
});
</script>

<style scoped>
.rqp {
  padding: 24px 28px 32px;
}

.rqp__header {
  margin-bottom: 20px;
}

.rqp__title {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.rqp__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.rqp__code {
  padding: 1px 6px;
  font-size: 0.8125rem;
  border-radius: 4px;
  background: var(--dsms-fill-light, #f5f7fa);
  color: var(--dsms-text);
}

.rqp__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.rqp__table {
  width: 100%;
}

.rqp__expand {
  padding: 8px 16px 12px 56px;
}

.rqp__expand-label {
  margin: 0 0 8px;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.rqp__options-editor {
  width: 100%;
}

.rqp__option-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.rqp__option-index {
  flex: 0 0 1.5rem;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
  text-align: right;
}

.rqp__option-row .el-input {
  flex: 1;
}

.rqp__add-option {
  margin-top: 4px;
}
</style>
