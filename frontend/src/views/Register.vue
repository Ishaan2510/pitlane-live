<template>
  <div class="auth-shell">
    <!-- Decorative left panel -->
    <div class="panel-left" aria-hidden="true">
      <div class="panel-year">2026</div>
      <div class="panel-tagline">JOIN<br>THE GRID.</div>
      <div class="panel-stats">
        <div class="stat">
          <span class="stat-num">24</span>
          <span class="stat-label">ROUNDS</span>
        </div>
        <div class="stat">
          <span class="stat-num">20</span>
          <span class="stat-label">DRIVERS</span>
        </div>
        <div class="stat">
          <span class="stat-num">∞</span>
          <span class="stat-label">PREDICTIONS</span>
        </div>
      </div>
    </div>

    <!-- Auth form -->
    <div class="panel-right">
      <router-link to="/" class="back-link">← PITLANE</router-link>

      <div class="form-wrap">
        <div class="form-header">
          <span class="form-round">NEW DRIVER</span>
          <h1 class="form-title">REGISTER</h1>
          <p class="form-sub">Create your account to start predicting</p>
        </div>

        <form @submit.prevent="submit" class="form" novalidate>
          <div class="field" :class="{ error: errors.username }">
            <label>USERNAME</label>
            <input
              v-model="form.username"
              type="text"
              placeholder="max_verstappen"
              autocomplete="username"
              @input="errors.username = ''"
            />
            <span class="field-error">{{ errors.username }}</span>
          </div>

          <div class="field" :class="{ error: errors.email }">
            <label>EMAIL</label>
            <input
              v-model="form.email"
              type="email"
              placeholder="you@example.com"
              autocomplete="email"
              @input="errors.email = ''"
            />
            <span class="field-error">{{ errors.email }}</span>
          </div>

          <div class="field" :class="{ error: errors.password }">
            <label>PASSWORD</label>
            <div class="input-wrap">
              <input
                v-model="form.password"
                :type="showPwd ? 'text' : 'password'"
                placeholder="Min. 6 characters"
                autocomplete="new-password"
                @input="errors.password = ''"
              />
              <button type="button" class="toggle-pwd" @click="showPwd = !showPwd">
                {{ showPwd ? 'HIDE' : 'SHOW' }}
              </button>
            </div>
            <div class="strength-bar">
              <span v-for="n in 4" :key="n" class="strength-seg" :class="strengthClass(n)"></span>
            </div>
            <span class="field-error">{{ errors.password }}</span>
          </div>

          <div v-if="serverError" class="server-error">
            <span class="err-pip"></span>{{ serverError }}
          </div>

          <button type="submit" class="btn-submit" :class="{ loading }" :disabled="loading">
            <span v-if="!loading">JOIN THE GRID</span>
            <span v-else class="spinner"></span>
          </button>
        </form>

        <div class="form-footer">
          Already in? <router-link to="/login">SIGN IN →</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth   = useAuthStore()

const form        = reactive({ username: '', email: '', password: '' })
const errors      = reactive({ username: '', email: '', password: '' })
const serverError = ref('')
const loading     = ref(false)
const showPwd     = ref(false)

const passwordStrength = computed(() => {
  const p = form.password
  if (!p) return 0
  let s = 0
  if (p.length >= 6)  s++
  if (p.length >= 10) s++
  if (/[A-Z]/.test(p) || /[0-9]/.test(p)) s++
  if (/[^A-Za-z0-9]/.test(p)) s++
  return s
})

function strengthClass(n) {
  if (n > passwordStrength.value) return ''
  if (passwordStrength.value <= 1) return 'weak'
  if (passwordStrength.value <= 2) return 'fair'
  if (passwordStrength.value <= 3) return 'good'
  return 'strong'
}

function validate() {
  let ok = true
  if (!form.username.trim()) {
    errors.username = 'Required'; ok = false
  } else if (form.username.trim().length < 3) {
    errors.username = 'Min 3 characters'; ok = false
  }
  if (!form.email.trim()) {
    errors.email = 'Required'; ok = false
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.email = 'Invalid email'; ok = false
  }
  if (!form.password) {
    errors.password = 'Required'; ok = false
  } else if (form.password.length < 6) {
    errors.password = 'Min 6 characters'; ok = false
  }
  return ok
}

async function submit() {
  serverError.value = ''
  if (!validate()) return
  loading.value = true
  try {
    await auth.register(form.username.trim(), form.email.trim().toLowerCase(), form.password)
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

.auth-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #0a0a0a;
  color: #e8e8e8;
  font-family: 'DM Mono', monospace;
}

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

.panel-stats {
  display: flex;
  gap: 32px;
  position: relative;
}

.stat { display: flex; flex-direction: column; gap: 4px; }

.stat-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 36px;
  line-height: 1;
  color: #e8e8e8;
}

.stat-label {
  font-size: 9px;
  letter-spacing: 2px;
  color: #444;
}

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

.form-header { margin-bottom: 36px; }

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

.field { margin-bottom: 22px; }

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

.input-wrap { position: relative; }
.input-wrap input { padding-right: 60px; }

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

/* Password strength bar */
.strength-bar {
  display: flex;
  gap: 4px;
  margin-top: 6px;
}

.strength-seg {
  flex: 1;
  height: 3px;
  background: #222;
  transition: background 0.3s;
}

.strength-seg.weak   { background: #c0392b; }
.strength-seg.fair   { background: #e67e22; }
.strength-seg.good   { background: #f1c40f; }
.strength-seg.strong { background: #27ae60; }

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

@media (max-width: 768px) {
  .auth-shell { grid-template-columns: 1fr; }
  .panel-left  { display: none; }
  .panel-right { padding: 40px 28px; }
}
</style>