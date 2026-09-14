<template>
  <!-- Login Screen -->
  <div v-if="!isLoggedIn" class="min-h-screen flex items-center justify-center bg-[#0B0F19] px-4 relative overflow-hidden">
    <!-- Neon Background Accents -->
    <div class="absolute w-[500px] h-[500px] rounded-full bg-indigo-600/10 blur-[120px] -top-40 -left-40"></div>
    <div class="absolute w-[500px] h-[500px] rounded-full bg-purple-600/10 blur-[120px] -bottom-40 -right-40"></div>

    <div class="w-full max-w-md bg-[#151B2C]/80 border border-[#1E293B] backdrop-blur-xl rounded-2xl p-8 shadow-[0_0_50px_-12px_rgba(99,102,241,0.3)] z-10">
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-purple-600 text-white text-3xl shadow-lg shadow-indigo-500/30 mb-4 animate-pulse">
          ⚡
        </div>
        <h1 class="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
          WattDash
        </h1>
        <p class="text-slate-400 text-sm mt-2">智能电费监测分析平台</p>
      </div>

      <el-form :model="loginForm" label-position="top" size="large">
        <el-form-item label="用户名">
          <el-input v-model="loginForm.username" placeholder="请输入用户名" prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码" prefix-icon="Lock" />
        </el-form-item>
        <div class="mt-8">
          <button 
            type="button" 
            @click="handleLogin" 
            :disabled="loginLoading"
            class="w-full py-3 px-4 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-semibold rounded-lg shadow-lg shadow-indigo-500/25 transition duration-300 transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loginLoading">正在安全登录...</span>
            <span v-else>立即登录</span>
          </button>
        </div>
      </el-form>
      <div class="text-center mt-6 text-xs text-slate-500">
        默认凭证: admin / admin (首次登录后建议修改)
      </div>
    </div>
  </div>

  <!-- Dashboard App -->
  <div v-else class="min-h-screen bg-[#0B0F19] text-[#F8FAFC]">
    <!-- Header -->
    <header class="sticky top-0 z-40 backdrop-blur-md bg-[#0F172A]/80 border-b border-[#1E293B]">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <span class="text-2xl">⚡</span>
          <span class="text-xl font-bold tracking-tight bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">WattDash</span>
        </div>
        <div class="flex items-center space-x-4">
          <span class="hidden md:inline text-sm text-slate-400">
            欢迎回来，<span class="text-indigo-400 font-medium">{{ userInfo.username }}</span>
          </span>
          <button 
            @click="openSettingsModal" 
            class="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-[#1E293B] transition duration-200"
            title="网关设置"
          >
            <el-icon :size="20"><Setting /></el-icon>
          </button>
          <button 
            @click="handleLogout" 
            class="flex items-center space-x-1 py-1.5 px-3 border border-red-500/30 hover:border-red-500/60 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-sm font-medium rounded-lg transition duration-200"
          >
            <el-icon><SwitchButton /></el-icon>
            <span>退出</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      
      <!-- Flashing Anomaly Alert -->
      <div 
        v-if="overview.has_anomaly" 
        class="bg-gradient-to-r from-red-500/20 via-orange-500/15 to-red-500/20 border border-red-500/30 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between shadow-lg shadow-red-500/5 animate-pulse"
      >
        <div class="flex items-center space-x-3 mb-4 md:mb-0">
          <div class="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center text-red-500 text-lg">
            ⚠️
          </div>
          <div>
            <h4 class="text-red-400 font-bold">用电量计算检测到数据异常</h4>
            <p class="text-slate-300 text-sm mt-0.5">{{ overview.anomaly_reason }}</p>
          </div>
        </div>
        <div class="flex space-x-3">
          <button 
            @click="triggerRecalculate"
            :disabled="recalculateLoading"
            class="py-2 px-5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white font-semibold rounded-lg shadow-md transition duration-200 flex items-center space-x-1"
          >
            <el-icon v-if="recalculateLoading" class="animate-spin"><Loading /></el-icon>
            <span>{{ recalculateLoading ? '重算中...' : '重算今日数据' }}</span>
          </button>
          <button 
            @click="openRechargeModal"
            class="py-2 px-5 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg shadow-md transition duration-200"
          >
            立即补录充值
          </button>
        </div>
      </div>

      <!-- Stats Overview Cards Grid (4 Columns) -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        
        <!-- Card 1: Balance -->
        <div class="bg-[#151B2C]/80 border border-[#1E293B] rounded-2xl p-5 relative overflow-hidden group shadow-lg">
          <div class="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-bl-full group-hover:bg-indigo-500/10 transition duration-300"></div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-sm font-medium text-slate-400">当前电费余额</span>
            <span class="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400">实时</span>
          </div>
          <div class="flex items-baseline space-x-1">
            <span class="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              {{ overview.latest_balance_yuan }}
            </span>
            <span class="text-lg font-medium text-slate-400">元</span>
          </div>
          <!-- Balance status indicator bar -->
          <div class="mt-4 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div 
              class="h-full rounded-full transition-all duration-1000"
              :class="balanceStatusClass"
              :style="{ width: Math.min(100, (overview.latest_balance_yuan / 100) * 100) + '%' }"
            ></div>
          </div>
          <div class="flex justify-between items-center text-xs text-slate-500 mt-2">
            <span>剩余: <strong class="text-slate-300">{{ overview.latest_balance }}</strong> 度</span>
            <span>{{ balanceSafetyText }}</span>
          </div>
        </div>

        <!-- Card 2: Today Consumption -->
        <div class="bg-[#151B2C]/80 border border-[#1E293B] rounded-2xl p-5 relative overflow-hidden group shadow-lg">
          <div class="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-bl-full group-hover:bg-cyan-500/10 transition duration-300"></div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-sm font-medium text-slate-400">今日已用电量</span>
            <span class="text-xs px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400">今日实时</span>
          </div>
          <div class="flex items-baseline space-x-1">
            <span class="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
              {{ overview.today_consumption !== null && overview.today_consumption !== undefined ? overview.today_consumption : '--' }}
            </span>
            <span class="text-lg font-medium text-slate-400">度</span>
          </div>
          <div class="flex justify-between items-center text-xs text-slate-500 mt-5">
            <span>折合电费: <strong class="text-emerald-400">{{ overview.today_consumption_yuan !== null && overview.today_consumption_yuan !== undefined ? `¥${overview.today_consumption_yuan}` : '--' }}</strong></span>
            <span class="text-slate-500 text-[11px]">充值已自愈平抑</span>
          </div>
        </div>

        <!-- Card 3: Yesterday Consumption -->
        <div class="bg-[#151B2C]/80 border border-[#1E293B] rounded-2xl p-5 relative overflow-hidden group shadow-lg">
          <div class="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-bl-full group-hover:bg-blue-500/10 transition duration-300"></div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-sm font-medium text-slate-400">昨日全天耗电</span>
            <span class="text-xs px-2 py-0.5 rounded bg-blue-500/10 text-blue-400">日终结算</span>
          </div>
          <div class="flex items-baseline space-x-1">
            <span class="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
              {{ overview.yesterday_consumption !== null && overview.yesterday_consumption !== undefined ? overview.yesterday_consumption : '--' }}
            </span>
            <span class="text-lg font-medium text-slate-400">度</span>
          </div>
          <div class="flex justify-between items-center text-xs text-slate-500 mt-5">
            <span>昨日电费: <strong class="text-indigo-300">{{ overview.yesterday_consumption_yuan !== null && overview.yesterday_consumption_yuan !== undefined ? `¥${overview.yesterday_consumption_yuan}` : '--' }}</strong></span>
            <span>7天均: <strong class="text-slate-300">{{ overview.seven_day_avg || '--' }}</strong>度</span>
          </div>
        </div>

        <!-- Card 4: Month Cumulative -->
        <div class="bg-[#151B2C]/80 border border-[#1E293B] rounded-2xl p-5 relative overflow-hidden group shadow-lg">
          <div class="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-bl-full group-hover:bg-purple-500/10 transition duration-300"></div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-sm font-medium text-slate-400">本月累计耗电</span>
            <span class="text-xs px-2 py-0.5 rounded bg-purple-500/10 text-purple-400">自然月</span>
          </div>
          <div class="flex items-baseline space-x-1">
            <span class="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              {{ overview.month_cumulative_consumption }}
            </span>
            <span class="text-lg font-medium text-slate-400">度</span>
          </div>
          <div class="flex justify-between items-center text-xs text-slate-500 mt-5">
            <span>月度花费: <strong class="text-emerald-400">¥{{ overview.month_cumulative_consumption_yuan }}</strong></span>
            <span>日均: <strong class="text-slate-300">{{ dailyAverageConsumption }}</strong>度</span>
          </div>
        </div>

      </div>

      <!-- Quick Operations & Sync Control Bar -->
      <div class="bg-[#151B2C]/80 border border-[#1E293B] rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between shadow-lg gap-4">
        <div class="flex items-center space-x-3 text-xs text-slate-400">
          <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>自动同步状态: <strong class="text-emerald-400">定死 23:30 (APScheduler)</strong></span>
          <span class="text-slate-600">|</span>
          <span>更新时间: <strong class="text-slate-300">{{ overview.update_time }}</strong></span>
        </div>
        <div class="flex items-center space-x-3 w-full md:w-auto">
          <button 
            v-if="!queryLoading"
            @click="triggerManualQuery(0)" 
            class="flex-1 md:flex-initial py-2 px-4 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white text-xs font-semibold rounded-lg shadow-md transition duration-200 flex items-center justify-center space-x-1"
          >
            <span>一键刷新/查询</span>
          </button>
          <button 
            v-else
            @click="abortQuery" 
            class="flex-1 md:flex-initial py-2 px-4 bg-gradient-to-r from-red-500 to-pink-600 hover:from-red-600 hover:to-pink-700 text-white text-xs font-semibold rounded-lg shadow-md transition duration-200 flex items-center justify-center space-x-1 animate-pulse"
          >
            <el-icon class="animate-spin"><Loading /></el-icon>
            <span>手动停止查询</span>
          </button>
          <button 
            @click="openRechargeModal"
            class="flex-1 md:flex-initial py-2 px-4 border border-indigo-500/30 hover:border-indigo-500/60 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 text-xs font-semibold rounded-lg transition duration-200"
          >
            登记充值
          </button>
          <button 
            @click="triggerRecalculate"
            :disabled="recalculateLoading"
            class="py-2 px-3 border border-amber-500/30 hover:border-amber-500/60 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-xs font-semibold rounded-lg transition duration-200 disabled:opacity-50"
            title="重算今日耗电数据"
          >
            {{ recalculateLoading ? '重算中...' : '重算今日' }}
          </button>
        </div>
      </div>

      <!-- NEW SECTION: Daily Energy Consumption & Smart Analytics -->
      <div class="bg-[#151B2C]/80 border border-[#1E293B] rounded-2xl p-4 sm:p-6 shadow-xl space-y-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#1E293B]">
          <div>
            <h3 class="text-lg font-bold text-white flex items-center space-x-2">
              <span>📅</span>
              <span>每日耗电明细与用能分析</span>
            </h3>
            <p class="text-xs text-slate-400 mt-0.5">
              一眼掌握每天耗电量、折合电费及环比波动，配合续航预估与生活节能指南科学调优
            </p>
          </div>
          <div class="flex items-center space-x-3 mt-3 sm:mt-0">
            <span class="text-xs px-2.5 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300">
              近7天日均: <strong class="text-indigo-400">{{ overview.seven_day_avg || '--' }}</strong> 度/天
            </span>
            <button 
              @click="fetchDailyRecords"
              :disabled="dailyRecordsLoading"
              class="p-1.5 text-slate-400 hover:text-white bg-slate-800/50 hover:bg-slate-800 rounded-lg border border-slate-700 transition"
              title="刷新每日明细"
            >
              <el-icon :class="{ 'animate-spin': dailyRecordsLoading }"><Refresh /></el-icon>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <!-- Left Column: Daily Records Table (7 cols on desktop) -->
          <div class="lg:col-span-7">
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
                <span>📋</span>
                <span>每日用能速查清单</span>
              </h4>
              <span class="text-[11px] text-slate-500">显示最近 {{ dailyRecords.length }} 天结算数据</span>
            </div>
            
            <div class="overflow-x-auto rounded-xl border border-[#1E293B] bg-[#0B0F19]/60 max-h-[380px] overflow-y-auto">
              <table class="w-full text-left text-xs">
                <thead class="bg-[#151B2C] text-slate-400 border-b border-[#1E293B] sticky top-0 z-10">
                  <tr>
                    <th class="py-2.5 px-3">日期</th>
                    <th class="py-2.5 px-3">耗电量 (度)</th>
                    <th class="py-2.5 px-3">折合电费</th>
                    <th class="py-2.5 px-3">较前日波动</th>
                    <th class="py-2.5 px-3">结算结余</th>
                    <th class="py-2.5 px-3">状态/事件</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[#1E293B]/60 text-slate-200">
                  <tr v-if="dailyRecords.length === 0">
                    <td colspan="6" class="text-center py-10 text-slate-500">
                      {{ dailyRecordsLoading ? '正在加载每日明细...' : '暂无每日耗电记录' }}
                    </td>
                  </tr>
                  <tr 
                    v-else 
                    v-for="item in dailyRecords" 
                    :key="item.id"
                    class="hover:bg-slate-800/30 transition duration-150"
                  >
                    <td class="py-2.5 px-3 font-medium whitespace-nowrap">
                      <div class="flex items-center space-x-1.5">
                        <span class="text-slate-200">{{ item.date_display }}</span>
                        <span 
                          class="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                          :class="{
                            'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30': item.date_label === '今天',
                            'bg-purple-500/20 text-purple-400 border border-purple-500/30': item.date_label === '昨天',
                            'text-slate-500': item.date_label !== '今天' && item.date_label !== '昨天'
                          }"
                        >
                          {{ item.date_label }}
                        </span>
                      </div>
                    </td>
                    <td class="py-2.5 px-3 whitespace-nowrap">
                      <div class="flex items-center space-x-2">
                        <span class="font-bold text-sm" :class="item.consumption === null ? 'text-slate-500' : 'text-slate-100'">
                          {{ item.consumption !== null ? item.consumption.toFixed(2) : '--' }}
                        </span>
                        <span 
                          v-if="item.consumption !== null"
                          class="text-[10px] px-1.5 py-0.5 rounded"
                          :class="{
                            'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20': item.energy_level === 'low',
                            'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20': item.energy_level === 'normal',
                            'bg-rose-500/10 text-rose-400 border border-rose-500/20': item.energy_level === 'high',
                            'bg-slate-700/30 text-slate-400': item.energy_level === 'unknown'
                          }"
                        >
                          {{ item.energy_level_label }}
                        </span>
                      </div>
                    </td>
                    <td class="py-2.5 px-3 text-slate-300 font-mono whitespace-nowrap">
                      {{ item.consumption_yuan !== null ? `¥${item.consumption_yuan.toFixed(2)}` : '--' }}
                    </td>
                    <td class="py-2.5 px-3 whitespace-nowrap">
                      <span 
                        v-if="item.diff_from_yesterday !== null" 
                        class="flex items-center space-x-0.5 font-mono text-[11px]"
                        :class="item.diff_from_yesterday > 0 ? 'text-rose-400' : (item.diff_from_yesterday < 0 ? 'text-emerald-400' : 'text-slate-400')"
                      >
                        <span>{{ item.diff_from_yesterday > 0 ? '↑' : (item.diff_from_yesterday < 0 ? '↓' : '—') }}</span>
                        <span>{{ Math.abs(item.diff_from_yesterday).toFixed(1) }}度</span>
                      </span>
                      <span v-else class="text-slate-600">--</span>
                    </td>
                    <td class="py-2.5 px-3 text-slate-400 whitespace-nowrap font-mono text-[11px]">
                      {{ item.balance }} 度
                    </td>
                    <td class="py-2.5 px-3 whitespace-nowrap">
                      <span 
                        v-if="item.recharge_amount" 
                        class="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-semibold animate-pulse"
                      >
                        +{{ item.recharge_amount }}元充值
                      </span>
                      <span 
                        v-else-if="item.is_abnormal" 
                        class="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 border border-rose-500/40 text-rose-300"
                        :title="item.anomaly_reason"
                      >
                        异常
                      </span>
                      <span v-else class="text-slate-600 text-[10px]">正常</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Right Column: Endurance & Energy Saving Suggestions (5 cols on desktop) -->
          <div class="lg:col-span-5 flex flex-col justify-between space-y-4">
            <!-- Battery Endurance Card -->
            <div class="bg-[#0F172A]/70 border border-[#1E293B] rounded-xl p-4">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-semibold text-slate-400 flex items-center space-x-1.5">
                  <span>⚡</span>
                  <span>剩余电量续航测算</span>
                </span>
                <span 
                  class="text-[10px] px-2 py-0.5 rounded-full"
                  :class="{
                    'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30': overview.estimated_days_left && overview.estimated_days_left >= 7,
                    'bg-amber-500/10 text-amber-400 border border-amber-500/30': overview.estimated_days_left && overview.estimated_days_left < 7 && overview.estimated_days_left >= 3,
                    'bg-rose-500/10 text-rose-400 border border-rose-500/30': overview.estimated_days_left && overview.estimated_days_left < 3,
                    'bg-slate-800 text-slate-400': !overview.estimated_days_left
                  }"
                >
                  {{ overview.estimated_days_left ? (overview.estimated_days_left < 3 ? '续航偏紧' : '续航充裕') : '计算中' }}
                </span>
              </div>
              <div class="flex items-baseline space-x-2 my-2">
                <span class="text-3xl font-black bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
                  {{ overview.estimated_days_left !== null && overview.estimated_days_left !== undefined ? overview.estimated_days_left : '--' }}
                </span>
                <span class="text-slate-400 text-sm font-medium">天</span>
                <span v-if="overview.estimated_end_date" class="text-xs text-slate-500 ml-auto">
                  预计可用至: <span class="text-indigo-400 font-semibold">{{ overview.estimated_end_date }}</span>
                </span>
              </div>
              <div class="text-xs text-slate-400 leading-relaxed">
                测算基准：基于寝室近 7 天日均耗电 <span class="text-indigo-300 font-medium">{{ overview.seven_day_avg || '--' }}</span> 度（约 <span class="text-emerald-400 font-medium">¥{{ overview.seven_day_avg_yuan || '--' }}</span>/天）。
              </div>
            </div>

            <!-- Actionable Advice & Energy Saving Tips (看看怎么调整) -->
            <div class="bg-[#0F172A]/70 border border-[#1E293B] rounded-xl p-4 space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-xs font-semibold text-indigo-400 flex items-center space-x-1.5">
                  <span>💡</span>
                  <span>用能评估与调节建议</span>
                </span>
                <span 
                  class="text-[10px] px-2 py-0.5 rounded font-bold"
                  :class="{
                    'bg-emerald-500/20 text-emerald-400': overview.usage_level === 'low',
                    'bg-cyan-500/20 text-cyan-400': overview.usage_level === 'normal',
                    'bg-rose-500/20 text-rose-400': overview.usage_level === 'high',
                    'bg-slate-800 text-slate-400': !overview.usage_level
                  }"
                >
                  {{ overview.usage_level_label || '诊断中' }}
                </span>
              </div>

              <p class="text-xs text-slate-300 leading-relaxed bg-[#151B2C] p-2.5 rounded-lg border border-[#1E293B]">
                {{ overview.adjustment_advice || '生活用电处于正常合理区间。建议空调保持在 26℃，夜间配合定时或睡眠模式。' }}
              </p>

              <!-- Practical adjustments list -->
              <div class="text-[11px] text-slate-400 space-y-2 pt-1">
                <div class="flex items-start space-x-2">
                  <span class="text-cyan-400 font-bold">❄️</span>
                  <span><strong>空调控温：</strong>设定在 26℃ 配合定时睡眠，比 22℃ 每日可省约 1.5~2.5 度电。</span>
                </div>
                <div class="flex items-start space-x-2">
                  <span class="text-purple-400 font-bold">🔌</span>
                  <span><strong>待机排查：</strong>主机、显示器、充电插座关机不断电，每天产生约 0.3~0.5 度待机空耗。</span>
                </div>
                <div v-if="overview.recharge_reminder" class="flex items-start space-x-2 text-rose-400 font-medium">
                  <span>⚠️</span>
                  <span>{{ overview.recharge_reminder }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Trend Charts Panel -->
      <div class="bg-[#151B2C]/80 border border-[#1E293B] rounded-2xl p-4 sm:p-6 shadow-xl">
        <div class="flex flex-col sm:flex-row items-center justify-between mb-6 pb-4 border-b border-[#1E293B]">
          <div class="mb-4 sm:mb-0">
            <h3 class="text-lg font-bold text-white">用电量与余额趋势分析</h3>
            <p class="text-xs text-slate-400 mt-0.5">柱状图显示真实耗电（充值平抑修正），折线图展示余额变化</p>
          </div>
          <div class="flex flex-col md:flex-row items-center space-y-3 md:space-y-0 md:space-x-3">
            <div class="flex space-x-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
              <button 
                @click="setChartRange('today')"
                class="py-1.5 px-3 text-xs font-semibold rounded-md transition duration-200"
                :class="chartDays === 'today' ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-white'"
              >
                今日分时
              </button>
              <button 
                @click="setChartRange(7)"
                class="py-1.5 px-3 text-xs font-semibold rounded-md transition duration-200"
                :class="chartDays === 7 ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-white'"
              >
                7天
              </button>
              <button 
                @click="setChartRange(30)"
                class="py-1.5 px-3 text-xs font-semibold rounded-md transition duration-200"
                :class="chartDays === 30 ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-white'"
              >
                30天
              </button>
              <button 
                @click="setChartRange('custom')"
                class="py-1.5 px-3 text-xs font-semibold rounded-md transition duration-200"
                :class="chartDays === 'custom' ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-white'"
              >
                自定义
              </button>
            </div>
            
            <div v-if="chartDays === 'today'" class="w-full md:w-auto">
              <el-date-picker
                v-model="intradayDate"
                type="date"
                placeholder="选择查询日期"
                size="small"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                :disabled-date="disabledFutureDate"
                @change="drawTrendChart"
                class="!bg-slate-900 !border-slate-800 text-xs"
              />
            </div>
            <div v-else-if="chartDays === 'custom'" class="w-full md:w-auto">
              <el-date-picker
                v-model="customDateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                size="small"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                :disabled-date="disabledFutureDate"
                @change="drawTrendChart"
                class="!bg-slate-900 !border-slate-800 text-xs"
              />
            </div>
          </div>
        </div>
        
        <div v-loading="chartLoading" element-loading-background="transparent" class="w-full h-80 md:h-96 relative">
          <div ref="chartContainer" class="w-full h-full"></div>
        </div>
      </div>

      <!-- Recharge Records History -->
      <div class="bg-[#151B2C]/80 border border-[#1E293B] rounded-2xl p-6 shadow-xl">
        <div class="flex items-center justify-between mb-6 pb-4 border-b border-[#1E293B]">
          <div>
            <h3 class="text-lg font-bold text-white">历史充值流水</h3>
            <p class="text-xs text-slate-400 mt-0.5">显示手动登记记录及其与每日耗电量的计算状态</p>
          </div>
          <button 
            @click="openRechargeModal"
            class="flex items-center space-x-1 py-1.5 px-3 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-indigo-400 text-xs font-semibold rounded-lg transition duration-200"
          >
            <el-icon><Plus /></el-icon>
            <span>新增登记</span>
          </button>
        </div>

        <el-table :data="recharges" style="width: 100%">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="amount" label="充值金额 (元)">
            <template #default="scope">
              <span class="text-emerald-400 font-bold">+{{ scope.row.amount.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="recharge_date" label="充值时间">
            <template #default="scope">
              {{ formatDateTime(scope.row.recharge_date) }}
            </template>
          </el-table-column>
          <el-table-column prop="is_settled" label="结算状态">
            <template #default="scope">
              <el-tag :type="scope.row.is_settled ? 'success' : 'warning'" effect="dark" size="small">
                {{ scope.row.is_settled ? '已计算结算' : '待耗电比对' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="settled_at" label="结算时间">
            <template #default="scope">
              {{ scope.row.settled_at ? formatDateTime(scope.row.settled_at) : '--' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110" align="center">
            <template #default="scope">
              <el-popconfirm
                title="确定撤销此充值记录吗？撤销后系统将自动重新计算当日耗电量。"
                confirm-button-text="确定撤销"
                cancel-button-text="取消"
                confirm-button-type="danger"
                width="240"
                @confirm="handleDeleteRecharge(scope.row.id)"
              >
                <template #reference>
                  <button 
                    :disabled="rechargeDeleteLoading === scope.row.id"
                    class="text-xs px-2.5 py-1 text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg transition disabled:opacity-50"
                  >
                    {{ rechargeDeleteLoading === scope.row.id ? '撤销中...' : '撤销记录' }}
                  </button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Live Logs Console -->
      <div class="bg-[#151B2C]/80 border border-[#1E293B] rounded-2xl p-6 shadow-xl">
        <div class="flex items-center justify-between mb-4 pb-4 border-b border-[#1E293B]">
          <div>
            <h3 class="text-lg font-bold text-white flex items-center space-x-2">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>系统运行日志</span>
            </h3>
            <p class="text-xs text-slate-400 mt-0.5">详细记录学校网关登录、信任授权与耗电平衡算法的完整执行流</p>
          </div>
          <button 
            @click="clearLogs"
            class="py-1 px-3 border border-slate-700 hover:border-slate-500 bg-slate-800/40 hover:bg-slate-800 text-slate-400 text-xs font-semibold rounded-lg transition duration-200"
          >
            清空日志
          </button>
        </div>

        <div class="bg-[#0B0F19] border border-[#1E293B] rounded-xl p-4 h-48 overflow-y-auto font-mono text-xs space-y-1.5 select-text">
          <div v-if="systemLogs.length === 0" class="text-slate-600 text-center py-16">
            暂无日志信息，点击上方“一键刷新/查询”开始追踪执行细节。
          </div>
          <div 
            v-else 
            v-for="(log, idx) in systemLogs" 
            :key="idx" 
            class="flex items-start space-x-2 leading-relaxed"
            :class="{
              'text-emerald-400': log.type === 'success',
              'text-red-400': log.type === 'error',
              'text-yellow-400': log.type === 'warning',
              'text-slate-300': log.type === 'info'
            }"
          >
            <span class="text-slate-500">[{{ log.time }}]</span>
            <span class="font-bold flex-shrink-0 w-14" :class="{
              'text-emerald-500': log.type === 'success',
              'text-red-500': log.type === 'error',
              'text-yellow-500': log.type === 'warning',
              'text-slate-400': log.type === 'info'
            }">[{{ log.type.toUpperCase() }}]</span>
            <span class="break-all">{{ log.msg }}</span>
          </div>
        </div>
      </div>

    </main>

    <!-- Dialog: Manual Recharge -->
    <el-dialog v-model="rechargeModalVisible" title="⚡ 登记充值金额" width="450px" center>
      <el-form :model="rechargeForm" label-position="top">
        <el-form-item label="充值金额 (元)">
          <el-input-number 
            v-model="rechargeForm.amount" 
            :precision="2" 
            :step="10" 
            :min="0.01" 
            style="width: 100%" 
          />
        </el-form-item>
        <el-form-item label="充值日期">
          <el-date-picker
            v-model="rechargeForm.date"
            type="date"
            placeholder="选择充值发生的日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
          <div class="text-xs text-slate-500 mt-2">
            重要：系统将在下次同步或追溯结算中，使用该日期和金额平衡电表突增。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex space-x-3 justify-end">
          <button 
            @click="rechargeModalVisible = false" 
            class="py-2 px-4 border border-slate-700 bg-slate-800/30 hover:bg-slate-800 text-slate-400 rounded-lg text-sm transition"
          >
            取消
          </button>
          <button 
            @click="submitRecharge" 
            :disabled="rechargeSubmitLoading"
            class="py-2 px-5 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white rounded-lg text-sm font-semibold transition"
          >
            {{ rechargeSubmitLoading ? '提交中...' : '确认登记' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- Dialog: WeChat Verification Code (MFA) -->
    <el-dialog 
      v-model="mfaModalVisible" 
      title="🔒 需要企业微信二次验证" 
      width="400px" 
      center 
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div class="text-center py-2 space-y-4">
        <div class="text-indigo-400 text-sm">
          {{ mfaMsg }}
        </div>
        <el-input 
          v-model="mfaCode" 
          placeholder="请输入 6 位动态验证码" 
          maxlength="6" 
          class="text-center tracking-widest text-lg font-bold"
        />
        <div class="text-xs text-slate-500">
          验证码提交后，服务器将在 Linux 无头浏览器中智能接管、模拟信任设备，并将 Cookie 持久化缓存。
        </div>
      </div>
      <template #footer>
        <div class="flex space-x-3 justify-center w-full">
          <button 
            @click="cancelMfa" 
            class="flex-1 py-2 border border-slate-700 bg-slate-800/30 text-slate-400 rounded-lg text-sm transition"
          >
            中断查询
          </button>
          <button 
            @click="submitMfa" 
            :disabled="mfaSubmitLoading"
            class="flex-1 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg text-sm font-semibold transition"
          >
            {{ mfaSubmitLoading ? '验证授权中...' : '提交验证' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- Dialog: Settings -->
    <el-dialog v-model="settingsModalVisible" title="⚙️ 网关配置修改" width="550px" center>
      <el-form :model="settingsForm" label-position="top">
        <el-tabs type="card" class="settings-tabs">
          <el-tab-pane label="学校统一认证账密">
            <div class="space-y-4 pt-2">
              <el-form-item label="统一身份认证学号">
                <el-input v-model="settingsForm.student_id" placeholder="例如: 2022110000" />
              </el-form-item>
              <el-form-item label="统一身份认证密码">
                <el-input v-model="settingsForm.gateway_password" type="password" show-password placeholder="网关登录密码" />
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="settingsForm.save_login_screenshot">
                  自动登录成功时保存界面截图 (保存至 backend_data/success_screenshot.png，用于调试)
                </el-checkbox>
              </el-form-item>
            </div>
          </el-tab-pane>
          <el-tab-pane label="查询房间参数 (JSON)">
            <div class="space-y-4 pt-2">
              <el-form-item label="房间及校区配置参数 JSON">
                <el-input 
                  v-model="settingsForm.query_config_str" 
                  type="textarea" 
                  :rows="6" 
                  placeholder="请输入房间配置 JSON 对象" 
                />
              </el-form-item>
              <div class="text-xs text-slate-500">
                必须为合法的 JSON 格式。包含 aid, area, building, room 等字段。
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="修改控制台密码">
            <div class="space-y-4 pt-2">
              <el-form-item label="设置新控制台密码">
                <el-input v-model="settingsForm.password" type="password" show-password placeholder="不填表示不修改密码" />
              </el-form-item>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <div class="flex space-x-3 justify-end">
          <button 
            @click="settingsModalVisible = false" 
            class="py-2 px-4 border border-slate-700 bg-slate-800/30 text-slate-400 rounded-lg text-sm transition"
          >
            取消
          </button>
          <button 
            @click="saveSettings" 
            :disabled="settingsSaveLoading"
            class="py-2 px-5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg text-sm font-semibold transition"
          >
            {{ settingsSaveLoading ? '保存中...' : '保存修改' }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import request from '@/utils/request'

// Auth states
const isLoggedIn = ref(!!localStorage.getItem('token'))
const loginLoading = ref(false)
const loginForm = ref({
  username: '',
  password: ''
})
const userInfo = ref({
  username: '',
  student_id: '',
  query_config: {}
})

// Overview & table telemetry
const overview = ref({
  latest_balance: 0.0,
  latest_balance_yuan: 0.0,
  update_time: '暂无',
  month_cumulative_consumption: 0.0,
  month_cumulative_consumption_yuan: 0.0,
  has_anomaly: false,
  anomaly_reason: '',
  today_consumption: null,
  today_consumption_yuan: null,
  yesterday_consumption: null,
  yesterday_consumption_yuan: null,
  seven_day_avg: 0.0,
  seven_day_avg_yuan: 0.0,
  estimated_days_left: null,
  estimated_end_date: null,
  usage_level: 'normal',
  usage_level_label: '正常',
  adjustment_advice: '',
  recharge_reminder: null
})
const recharges = ref([])
const rechargeDeleteLoading = ref(null)

// Daily records table states
const dailyRecords = ref([])
const dailyRecordsLoading = ref(false)

const fetchDailyRecords = async () => {
  dailyRecordsLoading.value = true
  try {
    const data = await request.get('/statistics/daily?limit=15')
    dailyRecords.value = data
  } catch (err) {
    console.error('获取每日耗电明细失败:', err)
  } finally {
    dailyRecordsLoading.value = false
  }
}

// Rollback / Delete recharge handler
const handleDeleteRecharge = async (id) => {
  rechargeDeleteLoading.value = id
  addLog(`正在撤销充值记录 (ID: ${id}) 并重新平衡电表耗电...`, 'info')
  try {
    const res = await request.delete(`/recharge/${id}`)
    ElMessage.success(res.msg || '充值记录已成功撤销！耗电量已重新计算。')
    addLog(`[充值撤销成功] ${res.msg || ''}`, 'success')
    // Refresh all states
    await refreshMetrics()
    await fetchDailyRecords()
    await fetchRechargeHistory()
    await drawTrendChart()
    await fetchLogs()
  } catch (err) {
    ElMessage.error(err.message || '撤回充值记录失败')
    addLog(`撤回充值记录失败: ${err.message || '未知错误'}`, 'error')
  } finally {
    rechargeDeleteLoading.value = null
  }
}

// System logs console states with Database Persistence
const systemLogs = ref([])
const fetchLogs = async () => {
  try {
    const data = await request.get('/statistics/logs')
    systemLogs.value = data
  } catch (err) {
    console.error(err)
  }
}
let logQueue = Promise.resolve()
const addLog = async (message, type = 'info') => {
  const timeStr = new Date().toTimeString().split(' ')[0]
  // Pre-insert locally for instant UI update (optimistic update)
  systemLogs.value.unshift({ time: timeStr, msg: message, type })
  if (systemLogs.value.length > 100) {
    systemLogs.value.pop()
  }
  
  // Queue the backend API request so it runs sequentially and avoids SQLite lock contention
  logQueue = logQueue.then(async () => {
    try {
      const updatedLogs = await request.post('/statistics/logs', { message, level: type })
      systemLogs.value = updatedLogs
    } catch (err) {
      console.error(err)
    }
  })
}
const clearLogs = async () => {
  try {
    await request.delete('/statistics/logs')
    systemLogs.value = []
  } catch (err) {
    console.error(err)
  }
}

// Queries & Dialog loadings
const queryLoading = ref(false)
const isQueryAborted = ref(false)
const recalculateLoading = ref(false)
const rechargeModalVisible = ref(false)
const rechargeSubmitLoading = ref(false)
const rechargeForm = ref({
  amount: 50.0,
  date: ''
})

// MFA (Step 2) states
const mfaModalVisible = ref(false)
const mfaSubmitLoading = ref(false)
const mfaCode = ref('')
const mfaSessionId = ref('')
const mfaMsg = ref('')

// Settings states
const settingsModalVisible = ref(false)
const settingsSaveLoading = ref(false)
const settingsForm = ref({
  student_id: '',
  gateway_password: '',
  query_config_str: '',
  save_login_screenshot: false,
  password: ''
})

// ECharts states
const chartContainer = ref(null)
const chartDays = ref('today')
const chartLoading = ref(false)
let chartInstance = null

const intradayDate = ref(new Date().toISOString().split('T')[0])
const customDateRange = ref([
  new Date(Date.now() - 6 * 24 * 3600 * 1000).toISOString().split('T')[0],
  new Date().toISOString().split('T')[0]
])

const disabledFutureDate = (time) => {
  return time.getTime() > Date.now()
}

// Computed status helper for UI balance card
const balanceStatusClass = computed(() => {
  const b = overview.value.latest_balance_yuan
  if (b < 20) return 'bg-gradient-to-r from-red-500 to-orange-500'
  if (b < 50) return 'bg-gradient-to-r from-orange-400 to-yellow-400'
  return 'bg-gradient-to-r from-emerald-500 to-cyan-500'
})

const balanceSafetyText = computed(() => {
  const b = overview.value.latest_balance_yuan
  if (b < 20) return '极低 (需尽快充值)'
  if (b < 50) return '中等'
  return '充足'
})

const dailyAverageConsumption = computed(() => {
  const today = new Date().getDate()
  const val = overview.value.month_cumulative_consumption / (today || 1)
  return val.toFixed(2)
})

// Login handler
const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请输入完整账户密码')
    return
  }
  
  loginLoading.value = true
  try {
    const fd = new FormData()
    fd.append('username', loginForm.value.username)
    fd.append('password', loginForm.value.password)
    
    const data = await request.post('/auth/login', fd)
    localStorage.setItem('token', data.access_token)
    isLoggedIn.value = true
    ElMessage.success('登录成功')
    
    // Bootstrap data fetch
    await nextTick()
    await bootstrapDashboard()
  } catch (err) {
    console.error(err)
  } finally {
    loginLoading.value = false
  }
}

const handleLogout = () => {
  localStorage.removeItem('token')
  isLoggedIn.value = false
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  ElMessage.success('已安全登出')
}

// Fetch all dashboard overview metadata, recharges, daily records and charts
const bootstrapDashboard = async () => {
  await fetchUserProfile()
  await refreshMetrics()
  await fetchDailyRecords()
  await fetchRechargeHistory()
  await drawTrendChart()
  await fetchLogs()
}

const fetchUserProfile = async () => {
  try {
    const data = await request.get('/auth/me')
    userInfo.value = data
    settingsForm.value.student_id = data.student_id || ''
    
    const defaultQueryConfig = {
      aid: "0030000000002503",
      area: '{"area":"犀浦校区","areaname":"犀浦校区"}',
      building: '{"building":"鸿哲斋4号楼","buildingid":"1"}',
      floor: '{"floorid":"","floor":""}',
      room: '{"room":"","roomid":"041313"}'
    }
    
    // Use fallback if query_config is missing or empty
    const qc = (data.query_config && Object.keys(data.query_config).length > 0)
      ? data.query_config
      : defaultQueryConfig
      
    // Extract save_login_screenshot for local settings form checkbox
    settingsForm.value.save_login_screenshot = !!qc.save_login_screenshot
    
    // Keep raw JSON display clean by omitting the screenshot parameter from display text
    const cleanQc = { ...qc }
    delete cleanQc.save_login_screenshot
    
    settingsForm.value.query_config_str = JSON.stringify(cleanQc, null, 2)
  } catch (err) {
    console.error(err)
  }
}

const refreshMetrics = async () => {
  try {
    const data = await request.get('/statistics/overview')
    overview.value = data
  } catch (err) {
    console.error(err)
  }
}

const fetchRechargeHistory = async () => {
  try {
    const data = await request.get('/recharge')
    recharges.value = data
  } catch (err) {
    console.error(err)
  }
}

const abortQuery = () => {
  isQueryAborted.value = true
  queryLoading.value = false
  addLog('用户手动中止了刷新流程，正在停止浏览器与连接...', 'warning')
}

// Manual Sync (Query) logic with MFA flow integration
const triggerManualQuery = async (retryCount = 0) => {
  // Safeguard: default to 0 if retryCount is not a number (e.g. if it is a MouseEvent)
  const count = typeof retryCount === 'number' ? retryCount : 0
  
  if (count === 0) {
    isQueryAborted.value = false // Reset abort flag on new manual execution
  }
  
  if (isQueryAborted.value) {
    addLog('同步流已被用户手动终止。', 'warning')
    queryLoading.value = false
    return
  }
  
  if (count >= 2) {
    addLog('自动刷新凭证后仍然验证失败，已拦截退出以防止尝试过多被学校冻结账号！', 'error')
    ElMessage.error('自动刷新凭证后查询仍然失效，已停止查询以防止账号冻结。请检查学校网关账密。')
    queryLoading.value = false
    return
  }
  
  queryLoading.value = true
  if (count === 0) {
    addLog('发起电费手动刷新，正在建立请求连接...', 'info')
  } else {
    addLog('正在使用新提取的会话 Cookie 重新执行电费查询...', 'info')
  }
  
  try {
    const res = await request.get('/query')
    
    if (isQueryAborted.value) {
      addLog('同步流已被用户手动终止。', 'warning')
      queryLoading.value = false
      return
    }
    
    if (res.status === 'expired') {
      addLog('后端检测到本地 JSESSIONID 凭证超时失效。', 'warning')
      addLog('正在启动后台无头浏览器尝试自动静默登录与 SSO 刷新...', 'info')
      
      // Use extended timeout (3 minutes) for login-step1 because headless browser
      // startup, page loading, and cookie extraction can take well over 60 seconds.
      const step1Res = await request.post('/query/login-step1', null, { timeout: 180000 })
      
      if (isQueryAborted.value) {
        addLog('同步流已被用户手动终止。', 'warning')
        queryLoading.value = false
        return
      }
      
      if (step1Res.status === 'need_sms') {
        addLog('学校网关认证要求多因子验证，已在手机端触发企业微信动态验证码。', 'warning')
        addLog('等待用户填入 6 位验证码以授权信任设备...', 'warning')
        
        mfaSessionId.value = step1Res.session_id
        mfaMsg.value = step1Res.msg
        mfaCode.value = ''
        mfaModalVisible.value = true
        queryLoading.value = false
      } else if (step1Res.status === 'success') {
        addLog(`网关登录成功: ${step1Res.msg}`, 'success')
        if (step1Res.power !== undefined && step1Res.record) {
          const p = step1Res.power
          const r = step1Res.record
          addLog(`同步完成！获取最新余额: ${p} 元。`, 'success')
          if (r.is_abnormal) {
            addLog(`[警告] 余额计算异常: ${r.anomaly_reason}`, 'warning')
          } else {
            addLog(`[自愈计算] 今日耗电量: ${r.consumption !== null ? r.consumption.toFixed(2) + ' 元' : '-- 元'}。`, 'success')
          }
          await refreshMetrics()
          await fetchDailyRecords()
          await fetchRechargeHistory()
          await drawTrendChart()
          queryLoading.value = false
        } else {
          addLog('正在保存新 Cookie 并重试查询...', 'info')
          await triggerManualQuery(count + 1)
        }
      } else {
        throw new Error(step1Res.msg || '自动重连失败')
      }
    } else if (res.status === 'success') {
      const p = res.power
      const r = res.record
      addLog(`同步完成！获取最新余额: ${p} 元。`, 'success')
      if (r.is_abnormal) {
        addLog(`[警告] 余额计算异常: ${r.anomaly_reason}`, 'warning')
      } else {
        addLog(`[自愈计算] 今日耗电量: ${r.consumption !== null ? r.consumption.toFixed(2) + ' 元' : '-- 元'}。`, 'success')
      }
      
      await refreshMetrics()
      await fetchDailyRecords()
      await fetchRechargeHistory()
      await drawTrendChart()
      queryLoading.value = false
    } else {
      throw new Error(res.msg || '接口未知错误')
    }
  } catch (err) {
    // Auto-retry once on timeout or network errors (not on business logic errors)
    const isTimeout = err.code === 'ECONNABORTED' || (err.message && err.message.includes('timeout'))
    const isNetworkError = err.message === 'Network Error'
    
    if ((isTimeout || isNetworkError) && count === 0 && !isQueryAborted.value) {
      addLog(`请求超时或网络异常，将在 5 秒后自动重试...`, 'warning')
      await new Promise(resolve => setTimeout(resolve, 5000))
      if (!isQueryAborted.value) {
        await triggerManualQuery(count + 1)
        return
      }
    }
    
    addLog(`刷新失败: ${err.message || '网络连接异常'}`, 'error')
    ElMessage.error(err.message || '网关同步失败')
    queryLoading.value = false
  }
}

const submitMfa = async () => {
  if (!mfaCode.value || mfaCode.value.length !== 6) {
    ElMessage.warning('请输入完整的6位动态验证码')
    return
  }
  
  mfaSubmitLoading.value = true
  addLog(`正在提交动态码: ${mfaCode.value} 并授权信任设备...`, 'info')
  try {
    const res = await request.post('/query/login-step2', {
      session_id: mfaSessionId.value,
      sms_code: mfaCode.value
    })
    
    if (res.status === 'success') {
      mfaModalVisible.value = false
      addLog('企业微信验证码校对通过，已成功在 Linux Headless 中模拟点击信任该设备！', 'success')
      // Retrigger normal query
      await triggerManualQuery(0)
    } else {
      throw new Error(res.msg || '验证失败')
    }
  } catch (err) {
    addLog(`MFA 验证授权失败: ${err.message || '验证码错误'}`, 'error')
    ElMessage.error(err.message || 'MFA验证失败')
  } finally {
    mfaSubmitLoading.value = false
  }
}

const cancelMfa = () => {
  mfaModalVisible.value = false
  addLog('用户中断了 MFA 二次验证输入，授权被取消。', 'warning')
  ElMessage.warning('网关查询中断，设备授权失败')
}

// Recharge submit
const openRechargeModal = () => {
  rechargeForm.value.amount = 50.0
  rechargeForm.value.date = new Date().toISOString().split('T')[0] // default to today in local time zone ISO
  rechargeModalVisible.value = true
}

const submitRecharge = async () => {
  rechargeSubmitLoading.value = true
  addLog(`发起手动充值记账登记: 金额 = ${rechargeForm.value.amount} 元, 日期 = ${rechargeForm.value.date}...`, 'info')
  try {
    await request.post('/recharge', {
      amount: rechargeForm.value.amount,
      recharge_date: rechargeForm.value.date ? `${rechargeForm.value.date}T12:00:00` : null
    })
    
    addLog(`充值记账成功！金额 = ${rechargeForm.value.amount} 元，已触发系统执行历史追溯计算。`, 'success')
    ElMessage.success('登记充值成功！耗电计算已自动追溯平衡。')
    rechargeModalVisible.value = false
    
    // Refresh all states
    await refreshMetrics()
    await fetchDailyRecords()
    await fetchRechargeHistory()
    await drawTrendChart()
  } catch (err) {
    addLog(`充值登记失败: ${err.message || '网络连接异常'}`, 'error')
    console.error(err)
  } finally {
    rechargeSubmitLoading.value = false
  }
}

// Manual Recalculation
const triggerRecalculate = async () => {
  recalculateLoading.value = true
  addLog('用户手动触发今日数据重算...', 'info')
  try {
    const res = await request.post('/statistics/recalculate')
    if (res.status === 'success') {
      addLog(`[重算完成] ${res.msg}`, 'success')
      ElMessage.success(res.msg)
    } else {
      addLog(`[重算失败] ${res.msg}`, 'error')
      ElMessage.error(res.msg)
    }
    // Refresh all dashboard data
    await refreshMetrics()
    await fetchDailyRecords()
    await fetchRechargeHistory()
    await drawTrendChart()
    await fetchLogs()
  } catch (err) {
    addLog(`重算请求失败: ${err.message || '网络连接异常'}`, 'error')
    ElMessage.error(err.message || '重算失败')
  } finally {
    recalculateLoading.value = false
  }
}

// Settings Update
const openSettingsModal = () => {
  settingsForm.value.password = ''
  settingsModalVisible.value = true
}

const saveSettings = async () => {
  settingsSaveLoading.value = true
  try {
    let qc = null
    try {
      qc = JSON.parse(settingsForm.value.query_config_str)
    } catch (e) {
      throw new Error('查询房间参数必须是合法的 JSON 格式。')
    }
    
    // Inject local checkbox state back into the config sent to backend
    qc.save_login_screenshot = settingsForm.value.save_login_screenshot
    
    const payload = {
      student_id: settingsForm.value.student_id,
      gateway_password: settingsForm.value.gateway_password || undefined,
      query_config: qc
    }
    
    if (settingsForm.value.password) {
      payload.password = settingsForm.value.password
    }
    
    await request.put('/auth/me', payload)
    ElMessage.success('配置修改成功！已保存。')
    settingsModalVisible.value = false
    await bootstrapDashboard()
  } catch (err) {
    ElMessage.error(err.message || '修改配置失败')
  } finally {
    settingsSaveLoading.value = false
  }
}

// ECharts drawing
const drawTrendChart = async () => {
  chartLoading.value = true
  try {
    let data
    const isToday = chartDays.value === 'today'
    if (isToday) {
      data = await request.get(`/statistics/intraday?date=${intradayDate.value}`)
    } else if (chartDays.value === 'custom') {
      if (customDateRange.value && customDateRange.value.length === 2) {
        data = await request.get(`/statistics/trends?start_date=${customDateRange.value[0]}&end_date=${customDateRange.value[1]}`)
      } else {
        data = await request.get(`/statistics/trends?days=7`)
      }
    } else {
      data = await request.get(`/statistics/trends?days=${chartDays.value}`)
    }
    
    await nextTick()
    if (!chartContainer.value) return
    
    if (!chartInstance) {
      chartInstance = echarts.init(chartContainer.value)
    }
    
    // Clear previous option to prevent axis mixing issues when toggling chart types
    chartInstance.clear()
    
    let zoomStart = 0
    if (isToday && data.times && data.times.length > 8) {
      zoomStart = Math.max(0, 100 - (8 / data.times.length) * 100)
    } else if (!isToday && data.dates && data.dates.length > 10) {
      zoomStart = Math.max(0, 100 - (10 / data.dates.length) * 100)
    }

    let option
    if (isToday) {
      option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross',
            crossStyle: {
              color: '#4B5563'
            }
          },
          backgroundColor: '#1E293B',
          borderColor: '#334155',
          textStyle: {
            color: '#F8FAFC'
          }
        },
        legend: {
          data: ['分时余额 (元)', '分时电量 (度)'],
          textStyle: {
            color: '#94A3B8',
            fontSize: 10
          },
          bottom: 0,
          itemWidth: 12,
          itemHeight: 8
        },
        grid: {
          left: '3%',
          right: '3%',
          bottom: 60,
          top: '12%',
          containLabel: true
        },
        dataZoom: [
          {
            type: 'inside',
            xAxisIndex: 0,
            start: zoomStart,
            end: 100,
            zoomOnMouseWheel: false,
            moveOnMouseMove: true
          },
          {
            type: 'slider',
            show: data.times && data.times.length > 8,
            xAxisIndex: 0,
            start: zoomStart,
            end: 100,
            height: 12,
            bottom: 22,
            handleSize: '100%',
            textStyle: {
              color: 'transparent'
            },
            borderColor: 'transparent',
            fillerColor: 'rgba(56, 189, 248, 0.15)',
            backgroundColor: 'rgba(30, 41, 59, 0.5)',
            handleStyle: {
              color: '#38BDF8'
            }
          }
        ],
        xAxis: [
          {
            type: 'category',
            data: data.times,
            axisLabel: {
              color: '#64748B'
            },
            axisLine: {
              lineStyle: {
                color: '#1E293B'
              }
            }
          }
        ],
        yAxis: [
          {
            type: 'value',
            name: '余额 (元)',
            scale: true,
            axisLabel: {
              color: '#64748B'
            },
            nameTextStyle: {
              color: '#94A3B8'
            },
            splitLine: {
              lineStyle: {
                color: '#1E293B'
              }
            }
          },
          {
            type: 'value',
            name: '电量 (度)',
            scale: true,
            axisLabel: {
              color: '#64748B'
            },
            nameTextStyle: {
              color: '#94A3B8'
            },
            splitLine: {
              show: false
            }
          }
        ],
        series: [
          {
            name: '分时余额 (元)',
            type: 'line',
            smooth: true,
            data: data.balances_yuan,
            label: {
              show: true,
              position: 'top',
              color: '#38BDF8',
              fontSize: 10,
              hideOverlap: true
            },
            itemStyle: {
              color: '#38BDF8'
            },
            lineStyle: {
              width: 3,
              shadowColor: 'rgba(56, 189, 248, 0.3)',
              shadowBlur: 10
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(56, 189, 248, 0.2)' },
                { offset: 1, color: 'rgba(56, 189, 248, 0)' }
              ])
            }
          },
          {
            name: '分时电量 (度)',
            type: 'line',
            smooth: true,
            yAxisIndex: 1,
            data: data.balances,
            label: {
              show: false
            },
            itemStyle: {
              color: '#A78BFA'
            },
            lineStyle: {
              width: 2,
              type: 'dashed'
            }
          }
        ]
      }
    } else {
      option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross',
            crossStyle: {
              color: '#4B5563'
            }
          },
          backgroundColor: '#1E293B',
          borderColor: '#334155',
          textStyle: {
            color: '#F8FAFC'
          }
        },
        legend: {
          data: ['电费余额 (元)', '当日耗电量 (度)'],
          textStyle: {
            color: '#94A3B8',
            fontSize: 10
          },
          bottom: 0,
          itemWidth: 12,
          itemHeight: 8
        },
        grid: {
          left: '3%',
          right: '3%',
          bottom: 60,
          top: '12%',
          containLabel: true
        },
        dataZoom: [
          {
            type: 'inside',
            xAxisIndex: 0,
            start: zoomStart,
            end: 100,
            zoomOnMouseWheel: false,
            moveOnMouseMove: true
          },
          {
            type: 'slider',
            show: data.dates && data.dates.length > 10,
            xAxisIndex: 0,
            start: zoomStart,
            end: 100,
            height: 12,
            bottom: 22,
            handleSize: '100%',
            textStyle: {
              color: 'transparent'
            },
            borderColor: 'transparent',
            fillerColor: 'rgba(192, 132, 252, 0.15)',
            backgroundColor: 'rgba(30, 41, 59, 0.5)',
            handleStyle: {
              color: '#C084FC'
            }
          }
        ],
        xAxis: [
          {
            type: 'category',
            data: data.dates,
            axisPointer: {
              type: 'shadow'
            },
            axisLabel: {
              color: '#64748B'
            },
            axisLine: {
              lineStyle: {
                color: '#1E293B'
              }
            }
          }
        ],
        yAxis: [
          {
            type: 'value',
            name: '余额 (元)',
            scale: true,
            axisLabel: {
              formatter: '{value}',
              color: '#64748B'
            },
            nameTextStyle: {
              color: '#94A3B8'
            },
            splitLine: {
              lineStyle: {
                color: '#1E293B'
              }
            }
          },
          {
            type: 'value',
            name: '耗电量 (度)',
            min: 0,
            axisLabel: {
              formatter: '{value}',
              color: '#64748B'
            },
            nameTextStyle: {
              color: '#94A3B8'
            },
            splitLine: {
              show: false
            }
          }
        ],
        series: [
          {
            name: '当日耗电量 (度)',
            type: 'bar',
            yAxisIndex: 1,
            data: data.consumptions,
            label: {
              show: true,
              position: 'insideTop',
              color: '#FFFFFF',
              fontSize: 10,
              hideOverlap: true,
              formatter: (params) => params.value !== null ? params.value.toFixed(1) : ''
            },
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#C084FC' },
                { offset: 1, color: '#818CF8' }
              ]),
              borderRadius: [4, 4, 0, 0]
            },
            barMaxWidth: 20
          },
          {
            name: '电费余额 (元)',
            type: 'line',
            smooth: true,
            data: data.balances_yuan,
            label: {
              show: true,
              position: 'top',
              color: '#38BDF8',
              fontSize: 10,
              hideOverlap: true
            },
            itemStyle: {
              color: '#38BDF8'
            },
            lineStyle: {
              width: 3,
              shadowColor: 'rgba(56, 189, 248, 0.3)',
              shadowBlur: 10
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(56, 189, 248, 0.2)' },
                { offset: 1, color: 'rgba(56, 189, 248, 0)' }
              ])
            }
          }
        ]
      }
    }
    
    chartInstance.setOption(option)
  } catch (err) {
    console.error(err)
  } finally {
    chartLoading.value = false
  }
}

const setChartRange = (days) => {
  chartDays.value = days
  drawTrendChart()
}

// Watch range and redraw if container sizes change
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

// Helper date formatting
const formatDateTime = (val) => {
  if (!val) return ''
  const d = new Date(val)
  return `${d.getMonth() + 1}-${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

// Global session expired catcher
const onAuthExpired = () => {
  handleLogout()
}

onMounted(() => {
  if (isLoggedIn.value) {
    bootstrapDashboard()
  }
  window.addEventListener('resize', handleResize)
  window.addEventListener('auth-expired', onAuthExpired)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('auth-expired', onAuthExpired)
  if (chartInstance) {
    chartInstance.dispose()
  }
})
</script>

<style scoped>
/* Scoped overrides if any */
:deep(.settings-tabs .el-tabs__item) {
  color: #94A3B8 !important;
}
:deep(.settings-tabs .el-tabs__item.is-active) {
  color: #6366F1 !important;
  font-weight: bold;
}
:deep(.settings-tabs .el-tabs__header) {
  border-bottom: 1px solid #1E293B !important;
}

/* Dark theme custom table overrides */
:deep(.el-table) {
  background-color: transparent !important;
  color: #F8FAFC !important;
}
:deep(.el-table th.el-table__cell) {
  background-color: rgba(15, 23, 42, 0.6) !important;
  color: #94A3B8 !important;
  border-bottom: 1px solid #1E293B !important;
}
:deep(.el-table tr) {
  background-color: transparent !important;
}
:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid #1E293B !important;
  color: #CBD5E1 !important;
  background-color: transparent !important;
}
:deep(.el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell) {
  background-color: rgba(30, 41, 59, 0.4) !important;
}
:deep(.el-table::before), :deep(.el-table__inner-wrapper::before) {
  display: none !important;
}
</style>
