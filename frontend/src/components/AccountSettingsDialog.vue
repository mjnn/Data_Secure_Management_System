<template>
  <el-dialog
    :model-value="modelValue"
    title="账号设置"
    :width="isFunctionFo ? '560px' : '480px'"
    align-center
    append-to-body
    :close-on-click-modal="false"
    @update:model-value="(v) => $emit('update:modelValue', v)"
    @open="onOpen"
  >
    <el-tabs v-model="activeTab" class="account-tabs dsms-animate-content-in">
      <el-tab-pane label="基本信息" name="profile">
        <el-form
          ref="profileFormRef"
          :model="profileForm"
          :rules="profileRules"
          label-position="top"
          @submit.prevent="onSaveProfile"
        >
          <el-form-item label="用户名">
            <el-input :model-value="profileForm.username" disabled />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="profileForm.email" maxlength="200" clearable />
          </el-form-item>
          <el-form-item label="姓名" prop="full_name">
            <el-input v-model="profileForm.full_name" maxlength="200" clearable />
          </el-form-item>
          <el-form-item label="部门" prop="department">
            <el-input v-model="profileForm.department" maxlength="200" clearable />
          </el-form-item>
          <div class="account-actions">
            <el-button
              type="primary"
              :loading="savingProfile"
              @click="onSaveProfile"
            >
              保存
            </el-button>
          </div>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="修改密码" name="password">
        <el-form
          ref="passwordFormRef"
          :model="passwordForm"
          :rules="passwordRules"
          label-position="top"
          @submit.prevent="onChangePassword"
        >
          <el-form-item label="原密码" prop="old_password">
            <el-input
              v-model="passwordForm.old_password"
              type="password"
              maxlength="128"
              show-password
              autocomplete="current-password"
            />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input
              v-model="passwordForm.new_password"
              type="password"
              maxlength="128"
              show-password
              autocomplete="new-password"
            />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirm_password">
            <el-input
              v-model="passwordForm.confirm_password"
              type="password"
              maxlength="128"
              show-password
              autocomplete="new-password"
            />
          </el-form-item>
          <div class="account-actions">
            <el-button
              type="primary"
              :loading="savingPassword"
              @click="onChangePassword"
            >
              保存
            </el-button>
          </div>
        </el-form>
      </el-tab-pane>

      <el-tab-pane v-if="isFunctionFo" label="负责功能" name="duty-function">
        <p class="duty-lead">
          同一业务功能可由<strong>多名功能 FO</strong>共同负责。登记、新功能申请与<strong>解除负责关系</strong>均须由<strong>数据安全 FO</strong>在<strong>审批管理</strong>中审核；解除仅在审核通过后生效。
          当前为演示：列表保存在本机浏览器，未调用服务端。
        </p>

        <div class="duty-section-title">当前负责的功能</div>
        <div v-if="dutyBindings.length === 0" class="duty-empty">暂无登记，请在下方选择功能后点击「保存登记」。</div>
        <ul v-else class="duty-binding-list" aria-label="已登记负责功能">
          <li v-for="(row, idx) in dutyBindings" :key="`${row.id}-${idx}`" class="duty-binding-row">
            <div class="duty-binding-main">
              <span class="duty-binding-name">{{ row.name }}</span>
              <el-tag v-if="row.unbindPending" type="warning" size="small" effect="plain">解除待审</el-tag>
            </div>
            <el-button
              type="danger"
              link
              size="small"
              :disabled="row.unbindPending"
              @click="onRequestUnbind(row)"
            >
              申请解除
            </el-button>
          </li>
        </ul>

        <el-divider />

        <el-form label-position="top" class="duty-form">
          <el-form-item label="登记负责功能（可多选多条，分别保存）">
            <el-select
              v-model="dutyFunctionKey"
              placeholder="请选择您负责的功能"
              clearable
              filterable
              style="width: 100%"
            >
              <el-option
                v-for="opt in dutyFunctionOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <div class="duty-row">
            <el-button type="primary" :disabled="!dutyFunctionKey" @click="onRegisterDutyFunction">
              保存登记
            </el-button>
            <el-button link type="primary" @click="applyDialogVisible = true">
              未找到？申请新功能
            </el-button>
          </div>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>

  <el-dialog
    v-model="applyDialogVisible"
    title="申请负责功能"
    width="440px"
    append-to-body
    align-center
    :close-on-click-modal="false"
    @closed="resetApplyForm"
  >
    <p class="apply-hint">
      提交后，将由<strong>数据安全 FO</strong>在<strong>审批管理</strong>中审批；同一功能可批准多名功能 FO 共同负责。（当前为前端演示，未调用接口）
    </p>
    <el-form label-position="top">
      <el-form-item label="申请的功能名称" required>
        <el-input v-model="applyForm.name" maxlength="120" placeholder="例如：售后配件库存查询" clearable />
      </el-form-item>
      <el-form-item label="说明">
        <el-input
          v-model="applyForm.note"
          type="textarea"
          :rows="3"
          maxlength="500"
          show-word-limit
          placeholder="简要说明业务场景或系统入口"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="applyDialogVisible = false">取消</el-button>
      <el-button type="primary" :disabled="!applyForm.name.trim()" @click="onSubmitApply">
        提交申请
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import api from "../api";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";

const DUTY_STORAGE_PREFIX = "dsms_fo_duty_bindings_v1_";

const props = defineProps({
  modelValue: { type: Boolean, default: false }
});
const emit = defineEmits(["update:modelValue", "profile-updated"]);

const activeTab = ref("profile");

const profileFormRef = ref(null);
const profileForm = reactive({
  username: "",
  email: "",
  full_name: "",
  department: ""
});
const savingProfile = ref(false);

const currentUserMe = ref(null);
const isFunctionFo = computed(
  () => effectivePlatformRole(currentUserMe.value) === PLATFORM_ROLE.FUNCTION_FO
);

const passwordFormRef = ref(null);
const passwordForm = reactive({
  old_password: "",
  new_password: "",
  confirm_password: ""
});
const savingPassword = ref(false);

/** 占位选项：后续可对接业务功能目录接口 */
const dutyFunctionOptions = [
  { value: "fn_order_query", label: "销售订单查询" },
  { value: "fn_customer_master", label: "客户主数据维护" },
  { value: "fn_schedule_board", label: "生产排程看板" },
  { value: "fn_parts_inventory", label: "售后配件库存查询" },
  { value: "fn_quality_trace", label: "质量追溯填报" }
];

/** @type {import('vue').Ref<Array<{ id: string, name: string, unbindPending: boolean }>>} */
const dutyBindings = ref([]);

const dutyFunctionKey = ref("");
const applyDialogVisible = ref(false);
const applyForm = reactive({ name: "", note: "" });

const profileRules = {
  email: [
    { required: true, message: "请输入邮箱", trigger: "blur" },
    { type: "email", message: "邮箱格式不正确", trigger: "blur" }
  ]
};

const passwordRules = {
  old_password: [{ required: true, message: "请输入原密码", trigger: "blur" }],
  new_password: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { min: 8, max: 128, message: "新密码长度需为 8 至 128 位", trigger: "blur" }
  ],
  confirm_password: [
    { required: true, message: "请再次输入新密码", trigger: "blur" },
    {
      validator: (_rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error("两次输入的新密码不一致"));
        } else {
          callback();
        }
      },
      trigger: "blur"
    }
  ]
};

function loadDutyBindings() {
  const u = profileForm.username;
  if (!u) {
    dutyBindings.value = [];
    return;
  }
  try {
    const raw = localStorage.getItem(DUTY_STORAGE_PREFIX + u);
    const parsed = raw ? JSON.parse(raw) : [];
    dutyBindings.value = Array.isArray(parsed)
      ? parsed.map((x) => ({
          id: String(x.id ?? ""),
          name: String(x.name ?? ""),
          unbindPending: Boolean(x.unbindPending)
        }))
      : [];
  } catch {
    dutyBindings.value = [];
  }
}

function persistDutyBindings() {
  const u = profileForm.username;
  if (!u) return;
  try {
    localStorage.setItem(DUTY_STORAGE_PREFIX + u, JSON.stringify(dutyBindings.value));
  } catch {
    /* ignore */
  }
}

const loadMe = async () => {
  try {
    const { data } = await api.get("/api/v1/users/me");
    currentUserMe.value = data;
    profileForm.username = data.username ?? "";
    profileForm.email = data.email ?? "";
    profileForm.full_name = data.full_name ?? "";
    profileForm.department = data.department ?? "";
    loadDutyBindings();
  } catch (error) {
    const detail = error.response?.data?.detail;
    ElMessage.error(typeof detail === "string" ? detail : "加载账号信息失败");
  }
};

const onOpen = () => {
  activeTab.value = "profile";
  passwordForm.old_password = "";
  passwordForm.new_password = "";
  passwordForm.confirm_password = "";
  dutyFunctionKey.value = "";
  applyDialogVisible.value = false;
  resetApplyForm();
  loadMe();
};

const onRegisterDutyFunction = () => {
  const id = dutyFunctionKey.value;
  if (!id) return;
  if (dutyBindings.value.some((b) => b.id === id && !b.unbindPending)) {
    ElMessage.warning("该功能已在您的负责列表中，无需重复登记");
    return;
  }
  if (dutyBindings.value.some((b) => b.id === id && b.unbindPending)) {
    ElMessage.warning("该功能的解除申请尚在审核中，请待审批结束后再操作");
    return;
  }
  const label = dutyFunctionOptions.find((o) => o.value === id)?.label ?? id;
  dutyBindings.value.push({ id, name: label, unbindPending: false });
  dutyFunctionKey.value = "";
  persistDutyBindings();
  ElMessage.success(
    `已登记负责功能「${label}」（演示：已写入本机；正式环境须经数据安全 FO 审批后方可与其他 FO 并行列名于目录）`
  );
};

const onRequestUnbind = async (row) => {
  if (row.unbindPending) return;
  try {
    await ElMessageBox.confirm(
      `确定提交解除申请？解除「${row.name}」的负责关系须由数据安全 FO 在审批管理中审核通过后方生效；在通过前您仍视为对该功能负责。（当前为演示，仅本机记录）`,
      "申请解除负责功能",
      {
        confirmButtonText: "提交解除申请",
        cancelButtonText: "取消",
        type: "warning"
      }
    );
  } catch {
    return;
  }
  row.unbindPending = true;
  persistDutyBindings();
  ElMessage.success("解除申请已提交（演示）。待数据安全 FO 审批通过后，负责关系即失效。");
};

const resetApplyForm = () => {
  applyForm.name = "";
  applyForm.note = "";
};

const onSubmitApply = () => {
  const name = applyForm.name.trim();
  if (!name) {
    ElMessage.warning("请填写申请的功能名称");
    return;
  }
  ElMessage.success(
    "申请已提交（前端演示）。后续版本将流转至数据安全 FO 的「审批管理」；同一功能可绑定多名功能 FO。"
  );
  applyDialogVisible.value = false;
  resetApplyForm();
};

const onSaveProfile = async () => {
  const formEl = profileFormRef.value;
  if (!formEl) return;
  try {
    await formEl.validate();
  } catch (_err) {
    return;
  }
  savingProfile.value = true;
  try {
    const { data } = await api.put("/api/v1/users/me", {
      email: profileForm.email,
      full_name: profileForm.full_name,
      department: profileForm.department
    });
    currentUserMe.value = data;
    ElMessage.success("基本信息已更新");
    emit("profile-updated", data);
  } catch (error) {
    const detail = error.response?.data?.detail;
    ElMessage.error(typeof detail === "string" ? detail : "更新失败，请稍后再试");
  } finally {
    savingProfile.value = false;
  }
};

const onChangePassword = async () => {
  const formEl = passwordFormRef.value;
  if (!formEl) return;
  try {
    await formEl.validate();
  } catch (_err) {
    return;
  }
  savingPassword.value = true;
  try {
    await api.post("/api/v1/users/me/password", {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    });
    ElMessage.success("密码已修改");
    passwordForm.old_password = "";
    passwordForm.new_password = "";
    passwordForm.confirm_password = "";
  } catch (error) {
    const detail = error.response?.data?.detail;
    ElMessage.error(typeof detail === "string" ? detail : "修改密码失败");
  } finally {
    savingPassword.value = false;
  }
};
</script>

<style scoped>
.account-tabs :deep(.el-tabs__nav-wrap)::after {
  background-color: var(--workspace-border);
}

.account-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
}

.duty-lead {
  margin: 0 0 16px;
  font-size: 0.875rem;
  line-height: 1.65;
  color: var(--dsms-text-secondary);
}

.duty-section-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--dsms-text);
  margin-bottom: 8px;
}

.duty-empty {
  font-size: 0.875rem;
  color: var(--dsms-text-secondary);
  padding: 12px 0 4px;
}

.duty-binding-list {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--workspace-border);
  border-radius: 6px;
  background: var(--workspace-surface-2);
}

.duty-binding-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--workspace-border);
}

.duty-binding-row:last-child {
  border-bottom: none;
}

.duty-binding-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.duty-binding-name {
  font-size: 0.875rem;
  color: var(--dsms-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.duty-form {
  margin-top: 4px;
}

.duty-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.apply-hint {
  margin: 0 0 16px;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}
</style>
