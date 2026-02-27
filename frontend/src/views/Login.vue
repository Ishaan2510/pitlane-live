<template>
  <div class="auth-shell">
    <!-- Decorative left panel -->
    <div class="panel-left" aria-hidden="true">
      <div class="panel-year">2026</div>
      <div class="panel-tagline">PREDICT. SCORE.<br>DOMINATE.</div>
      <div class="panel-rounds">
        <span v-for="n in 24" :key="n" class="round-pip" :class="{ lit: n <= 3 }">{{ String(n).padStart(2,'0') }}</span>
      </div>
    </div>

    <!-- Auth form -->
    <div class="panel-right">
      <router-link to="/" class="back-link">← PITLANE</router-link>

      <div class="form-wrap">
        <div class="form-header">
          <span class="form-round">AUTH</span>
          <h1 class="form-title">SIGN IN</h1>
          <p class="form-sub">Enter your credentials to access the grid</p>
        </div>

        <form @submit.prevent="submit" class="form" novalidate>
          <div class="field" :class="{ error: errors.identifier }">
            <label>USERNAME OR EMAIL</label>
            <input
              v-model="form.identifier"
              type="text"
              placeholder="max_verstappen"
              autocomplete="username"
              @input="errors.identifier = ''"
            />
            <span class="field-error">{{ errors.identifier }}</span>
          </div>

          <div class="field" :class="{ error: errors.password }">
            <label>PASSWORD</label>
            <div class="input-wrap">
              <input
                v-model="form.password"
                :type="showPwd ? 'text' : 'password'"
                placeholder="••••••••"
                autocomplete="current-password"
                @input="errors.password = ''"
              />
              <button type="button" class="toggle-pwd" @click="showPwd = !showPwd">
                {{ showPwd ? 'HIDE' : 'SHOW' }}
              </button>
            </div>
            <span class="field-error">{{ errors.password }}</span>
          </div>

          <div v-if="serverError" class="server-error">
            <span class="err-pip"></span>{{ serverError }}
          </div>

          <button type="submit" class="btn-submit" :class="{ loading }" :disabled="loading">
            <span v-if="!loading">ENTER THE GRID</span>
            <span v-else class="spinner"></span>
          </button>
        </form>

        <div class="form-footer">
          No account? <router-link to="/register">CREATE ONE →</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth   = useAuthStore()

const form        = reactive({ identifier: '', password: '' })
const errors      = reactive({ identifier: '', password: '' })
const serverError = ref('')
const loading     = ref(false)
const showPwd     = ref(false)

function validate() {
  let ok = true
  if (!form.identifier.trim()) { errors.identifier = 'Required'; ok = false }
  if (!form.password.trim())   { errors.password   = 'Required'; ok = false }
  return ok
}

async function submit() {
  serverError.value = ''
  if (!validate()) return
  loading.value = true
  try {
    await auth.login(form.identifier.trim(), form.password)
    router.push('/')
  } catch (e) {
    serverError.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&display=swap');

/* ── Shell ── */
.auth-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #0a0a0a;
  color: #e8e8e8;
  font-family: 'DM Mono', monospace;
}

/* ── Left panel ── */
.panel-left {
  background: #0e0e0e;
  border-right: 1px solid #1e1e1e;
  padding: 64px 56px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  position: relative;
}

.panel-left::before {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 39px,
    #161616 39px,
    #161616 40px
  );
  pointer-events: none;
}

.panel-year {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 180px;
  line-height: 1;
  color: #141414;
  letter-spacing: -4px;
  margin-top: -20px;
  position: relative;
}

.panel-tagline {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 52px;
  line-height: 1.05;
  letter-spacing: 2px;
  color: #e8202a;
  position: relative;
}

.panel-rounds {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  position: relative;
}

.round-pip {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: #333;
  padding: 4px 6px;
  border: 1px solid #1e1e1e;
  transition: color 0.2s, border-color 0.2s;
}

.round-pip.lit {
  color: #e8202a;
  border-color: #e8202a;
}

/* ── Right panel ── */
.panel-right {
  display: flex;
  flex-direction: column;
  padding: 40px 56px;
}

.back-link {
  font-size: 11px;
  letter-spacing: 2px;
  color: #555;
  text-decoration: none;
  transition: color 0.2s;
  align-self: flex-start;
}
.back-link:hover { color: #e8e8e8; }

.form-wrap {
  margin: auto 0;
  max-width: 380px;
}

.form-header { margin-bottom: 40px; }

.form-round {
  font-size: 11px;
  letter-spacing: 4px;
  color: #e8202a;
  display: block;
  margin-bottom: 12px;
}

.form-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 64px;
  margin: 0 0 8px;
  letter-spacing: 2px;
  color: #f0f0f0;
}

.form-sub {
  font-size: 12px;
  color: #555;
  margin: 0;
  letter-spacing: 0.5px;
}

/* ── Fields ── */
.field {
  margin-bottom: 24px;
}

.field label {
  display: block;
  font-size: 10px;
  letter-spacing: 2px;
  color: #555;
  margin-bottom: 8px;
}

.field input {
  width: 100%;
  background: #111;
  border: 1px solid #222;
  color: #e8e8e8;
  padding: 12px 14px;
  font-family: 'DM Mono', monospace;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.field input:focus { border-color: #e8202a; }
.field.error input  { border-color: #c0392b; }

.field-error {
  display: block;
  font-size: 10px;
  color: #c0392b;
  margin-top: 5px;
  letter-spacing: 0.5px;
  min-height: 14px;
}

.input-wrap {
  position: relative;
}

.input-wrap input {
  padding-right: 60px;
}

.toggle-pwd {
  position: absolute;
  right: 0;
  top: 0;
  height: 100%;
  padding: 0 14px;
  background: none;
  border: none;
  color: #555;
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  letter-spacing: 1px;
  cursor: pointer;
  transition: color 0.2s;
}
.toggle-pwd:hover { color: #e8e8e8; }

/* ── Server error ── */
.server-error {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #1a0a0a;
  border: 1px solid #c0392b;
  padding: 12px 14px;
  font-size: 12px;
  color: #e55;
  margin-bottom: 24px;
}

.err-pip {
  width: 6px;
  height: 6px;
  background: #e8202a;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ── Submit ── */
.btn-submit {
  width: 100%;
  background: #e8202a;
  color: #fff;
  border: none;
  padding: 14px;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 18px;
  letter-spacing: 3px;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 50px;
}

.btn-submit:hover:not(:disabled) { background: #c0181f; }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Footer ── */
.form-footer {
  margin-top: 28px;
  font-size: 12px;
  color: #444;
}

.form-footer a {
  color: #e8202a;
  text-decoration: none;
  letter-spacing: 1px;
}
.form-footer a:hover { text-decoration: underline; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .auth-shell { grid-template-columns: 1fr; }
  .panel-left  { display: none; }
  .panel-right { padding: 40px 28px; }
}
</style>