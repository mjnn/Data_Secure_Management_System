<template>
  <el-card class="fbb dsms-glass-panel" shadow="never">
    <template #header>
      <span class="fbb__title">业务功能绑定（须审批）</span>
    </template>
    <p class="fbb__hint">
      功能 FO 的绑定与解绑须向<strong>数据安全 FO</strong>申请，审批通过后生效。数据安全 FO 按业务功能<strong>下发填报任务</strong>（仅对已绑定 FO 的功能可下发）。
    </p>

    <p v-if="savedIds.length" class="fbb__saved">
      当前已生效绑定：<strong>{{ savedLabels }}</strong>
    </p>
    <el-alert v-else type="warning" :closable="false" show-icon title="尚无生效绑定" description="审批通过至少一项绑定后，方可开始填报任务。" />

    <el-alert
      v-if="hasPendingBindingApp"
      class="fbb__pending"
      type="info"
      :closable="false"
      show-icon
      title="绑定变更申请审批中"
      description="请等待数据安全 FO 在「审批管理」中处理；处理前无法再次提交。"
    />

    <el-form label-width="96px" class="fbb__form" @submit.prevent>
      <el-form-item label="目标绑定" required>
        <dsms-filterable-select
          v-model="draftIds"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="选择希望绑定的业务功能"
          class="fbb__select"
          :disabled="hasPendingBindingApp"
          aria-label="目标业务功能绑定"
        >
          <el-option v-for="f in functionOptions" :key="f.id" :label="f.name" :value="f.id" />
        </dsms-filterable-select>
      </el-form-item>
      <el-form-item label="申请说明">
        <el-input
          v-model="applyReason"
          type="textarea"
          :rows="2"
          maxlength="500"
          show-word-limit
          placeholder="可选：说明绑定/解绑原因"
          :disabled="hasPendingBindingApp"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" :disabled="hasPendingBindingApp" @click="onSubmitApplication">
          提交绑定变更申请
        </el-button>
        <el-button link type="primary" @click="goApproval">查看我的申请</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import DsmsFilterableSelect from "../DsmsFilterableSelect.vue";
import { ensurePortalTenantReady, usePortalTenantContext } from "../../composables/usePortalTenantContext.js";
import {
  fetchBusinessFunctions,
  fetchMyFoBindings,
  PORTAL_DATA_REFRESH_EVENT,
  submitFoBindingRequest
} from "../../api/portalApi.js";
import { submissionFunctionName } from "../../data/submissionTasksMock.js";

const emit = defineEmits(["updated"]);

const router = useRouter();
const { tenantId, spaceId, ready } = usePortalTenantContext();
const functionOptions = ref([]);
const draftIds = ref([]);
const savedIds = ref([]);
const applyReason = ref("");
const hasPendingBindingApp = ref(false);
const submitting = ref(false);

const savedLabels = computed(() =>
  savedIds.value.map((id) => functionOptions.value.find((f) => f.id === id)?.name || submissionFunctionName(id)).join("、")
);

async function reload() {
  if (!ready.value || !tenantId.value) return;
  try {
    const [functions, binding] = await Promise.all([
      fetchBusinessFunctions(tenantId.value, spaceId.value),
      fetchMyFoBindings(tenantId.value, spaceId.value)
    ]);
    functionOptions.value = functions;
    savedIds.value = binding.function_keys || [];
    draftIds.value = [...savedIds.value];
    hasPendingBindingApp.value = !!binding.has_pending_binding_request;
    emit("updated", [...savedIds.value]);
  } catch {
    /* 静默 */
  }
}

async function onSubmitApplication() {
  if (!ready.value || !tenantId.value) return;
  submitting.value = true;
  try {
    const data = await submitFoBindingRequest(
      tenantId.value,
      spaceId.value,
      draftIds.value,
      applyReason.value
    );
    ElMessage.success(data.message || "已提交绑定变更申请");
    applyReason.value = "";
    await reload();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "提交失败");
  } finally {
    submitting.value = false;
  }
}

function goApproval() {
  router.push({ name: "dashboard-approval" });
}

function onPortalRefresh() {
  reload();
}

onMounted(async () => {
  await ensurePortalTenantReady();
  reload();
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, onPortalRefresh);
});

onBeforeUnmount(() => {
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, onPortalRefresh);
});
</script>

<style scoped>
.fbb {
  margin-bottom: 20px;
  border: 1px solid var(--el-border-color, #dcdfe6);
}

.fbb__title {
  font-weight: 600;
  color: var(--dsms-text);
}

.fbb__hint {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.fbb__saved {
  margin: 0 0 12px;
  font-size: 0.875rem;
  color: var(--dsms-text);
}

.fbb__pending {
  margin-bottom: 12px;
}

.fbb__select {
  width: 100%;
  max-width: 480px;
}
</style>
