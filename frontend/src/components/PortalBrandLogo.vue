<template>
  <span class="dsms-portal-logo" aria-hidden="true">
    <img
      class="dsms-portal-logo__img"
      :src="displaySrc"
      alt=""
      width="36"
      height="36"
      decoding="async"
    />
  </span>
</template>

<script setup>
import { ref, watch } from "vue";
import logoUrl from "@dsms-ref/logo.png?url";
import { useDsmsTheme } from "../composables/useDsmsTheme";

const { isDark } = useDsmsTheme();

const displaySrc = ref(logoUrl);

/** 算法迭代时递增，避免 HMR/缓存仍用旧的整块涂白结果 */
const RASTER_VERSION = 3;
let cachedRasterVersion = -1;
let whiteLogoDataUrl = null;

function luminance(r, g, b) {
  return 0.299 * r + 0.587 * g + 0.114 * b;
}

function saturation(r, g, b) {
  const mx = Math.max(r, g, b);
  if (mx < 1e-6) return 0;
  const mn = Math.min(r, g, b);
  return (mx - mn) / mx;
}

/**
 * 深色顶栏用：先去掉浅色/低饱和底板（常见白底、浅灰、浅蓝垫片仍不透明），
 * 再按「黑稿 → 反白」思路：用暗度得到白字 alpha，避免整块 36×36 被涂实。
 */
function rasterDarkModeWhiteLogo(image) {
  const nw = image.naturalWidth;
  const nh = image.naturalHeight;
  if (!nw || !nh) return null;

  let w = nw;
  let h = nh;
  const maxDim = 384;
  if (Math.max(w, h) > maxDim) {
    if (w >= h) {
      h = Math.round((nh * maxDim) / nw);
      w = maxDim;
    } else {
      w = Math.round((nw * maxDim) / nh);
      h = maxDim;
    }
  }

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return null;

  ctx.clearRect(0, 0, w, h);
  ctx.drawImage(image, 0, 0, w, h);

  const imgData = ctx.getImageData(0, 0, w, h);
  const d = imgData.data;

  for (let i = 0; i < d.length; i += 4) {
    const r = d[i];
    const g = d[i + 1];
    const b = d[i + 2];
    const a = d[i + 3];

    if (a < 8) {
      d[i] = 0;
      d[i + 1] = 0;
      d[i + 2] = 0;
      d[i + 3] = 0;
      continue;
    }

    const L = luminance(r, g, b);
    const S = saturation(r, g, b);

    /* 浅色 + 低饱和 ≈ 底板（白、浅灰、浅蓝灰等），抠透明 */
    const isPlate =
      L >= 248 ||
      (L >= 180 && S <= 0.18) ||
      (L >= 192 && r >= 168 && g >= 168 && b >= 168 && S <= 0.25);

    if (isPlate) {
      d[i] = 0;
      d[i + 1] = 0;
      d[i + 2] = 0;
      d[i + 3] = 0;
      continue;
    }

    /* 暗度 → 白化强度（等价于先压黑再反色后叠在 alpha 上） */
    const ink = Math.min(1, Math.max(0, (255 - L) / 255 + 0.02));
    if (ink < 0.04) {
      d[i] = 0;
      d[i + 1] = 0;
      d[i + 2] = 0;
      d[i + 3] = 0;
      continue;
    }

    const aOut = Math.min(255, Math.round((a / 255) * ink * 255));
    if (aOut < 6) {
      d[i] = 0;
      d[i + 1] = 0;
      d[i + 2] = 0;
      d[i + 3] = 0;
      continue;
    }

    d[i] = 255;
    d[i + 1] = 255;
    d[i + 2] = 255;
    d[i + 3] = aOut;
  }

  ctx.putImageData(imgData, 0, 0);
  return canvas.toDataURL("image/png");
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

async function ensureWhiteLogoDataUrl() {
  if (whiteLogoDataUrl != null && cachedRasterVersion === RASTER_VERSION) {
    return whiteLogoDataUrl;
  }
  whiteLogoDataUrl = null;
  const img = await loadImage(logoUrl);
  const url = rasterDarkModeWhiteLogo(img);
  if (!url) throw new Error("logo raster failed");
  whiteLogoDataUrl = url;
  cachedRasterVersion = RASTER_VERSION;
  return whiteLogoDataUrl;
}

watch(
  isDark,
  async (dark) => {
    if (!dark) {
      displaySrc.value = logoUrl;
      return;
    }
    try {
      displaySrc.value = await ensureWhiteLogoDataUrl();
    } catch (_e) {
      displaySrc.value = logoUrl;
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.dsms-portal-logo {
  position: relative;
}

.dsms-portal-logo__img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
