**繁體中文** | [English](README.md)

# IR Honeycomb Blind 紅外線蜂巢簾

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

Home Assistant 自訂整合元件，使用 Broadlink 紅外線傳輸器控制**上下合蜂巢簾**（Top-Down Bottom-Up Honeycomb Blind）。

## 功能介紹

### 什麼是上下合蜂巢簾？

上下合蜂巢簾有兩個可獨立移動的軌道：
- **上簾邊**：從頂部往下遮蔽
- **下簾邊**：從底部往上收起

兩者之間是簾面，可以靈活調整遮蔽的區域。

### 控制方式

本整合提供兩種窗簾控制模式（可在設定中選擇啟用）：

#### 模式一：分離式控制（預設）

| 實體 | 類型 | 功能 | 說明 |
|------|------|------|------|
| `cover.xxx_position` | Cover | 下簾位置控制 | 0（全關）~ 100（全開） |
| `cover.xxx_ratio` | Cover | 上簾比例控制 | 0（不遮）~ 100（全遮） |

#### 模式二：單一窗簾（含傾斜控制）

| 實體 | 類型 | 功能 | 說明 |
|------|------|------|------|
| `cover.xxx_blind` | Cover | 整合控制 | Position = 下簾位置，Tilt = 上簾比例 |

此模式適合 HomeKit 等支援 Window Covering + Tilt 的平台，可在單一介面同時控制兩個軌道。

#### 共用實體

| 實體 | 類型 | 功能 | 說明 |
|------|------|------|------|
| `button.xxx_calibrate` | Button | 校正按鈕 | 按下即可執行校正 |
| `binary_sensor.xxx_moving` | Binary Sensor | 移動狀態 | 窗簾是否正在移動 |
| `sensor.xxx_moving_rail` | Sensor | 移動中軌道 | 正在移動的軌道（上 / 下 / 無） |
| `sensor.xxx_time_remaining` | Sensor | 剩餘時間 | 預估的剩餘移動時間 |
| `sensor.xxx_last_calibration` | Sensor | 上次校正 | 上次校正的時間戳記 |

**位置模型：**
- `POS` = 下簾邊的高度位置
- `R` = 上簾從頂部往下遮蔽的比例
- 上簾邊高度 = `100 - (100 - POS) × R / 100`

**範例：**
| R | POS | 效果 |
|---|-----|------|
| 0 | 0 | 全開（校正後初始狀態） |
| 100 | 0 | 完全遮蔽 |
| 50 | 50 | 下半部打開，上半部遮一半 |

## 特色

- **圖形化設定**：透過 Home Assistant UI 完成所有設定，無需編輯 YAML
- **彈性控制模式**：可選擇分離式（Position + Ratio）或單一窗簾（Position + Tilt）模式
- **HomeKit 完整支援**：單一窗簾模式支援 Window Covering + Tilt，可在 HomeKit 中完美控制
- **即時位置更新**：移動中即時顯示估算位置（可在設定中開關）
- **智慧碰撞處理**：移動前自動檢測並讓路，避免上下簾相撞
- **Debounce 機制**：連續拖拉滑桿時，只執行最後一次指令
- **中斷估算**：移動中被中斷時，根據已移動時間估算目前位置
- **聯動調整**：調整下簾位置後，自動依比例調整上簾位置
- **多窗簾支援**：每組窗簾獨立運作，可同時控制
- **共享遙控器**：多組窗簾可共用同一台 Broadlink，IR 指令自動排隊
- **位置持久化**：Home Assistant 重啟後自動恢復位置狀態
- **一鍵校正**：每組窗簾都有校正按鈕，按下即可重設位置
- **設定即時生效**：變更設定選項後自動重載，無需重啟
- **多語系**：支援英文、繁體中文介面

## 環境需求

- **Home Assistant** 2024.1.0 或更新版本
- **Broadlink 整合**：已在 Home Assistant 中設定好 Broadlink 紅外線傳輸器
- **IR 遙控碼**：已學習好窗簾遙控器的 5 個按鈕 IR 碼（Base64 格式）

### RF 支援（433 / 315 MHz）

如果你使用 **Broadlink RM Pro / RM4 Pro** 系列，本整合也支援 **RF（433 / 315 MHz）射頻遙控的窗簾**，無需額外設定。`remote.send_command` 服務會根據學習到的 code 內容自動判斷使用 IR 或 RF 發射 — 只需將學習到的 RF code 以相同的 `b64:` 格式填入即可。

### 如何取得 IR / RF 碼？

#### IR 碼

1. 在 Home Assistant 中進入 **開發者工具 > 服務**
2. 呼叫 `remote.learn_command` 服務，選擇你的 Broadlink 設備
3. 依照提示對準遙控器按下按鈕
4. 學習完成後，IR 碼會儲存在 Broadlink 整合中
5. 也可以使用第三方工具（如 Broadlink Manager）匯出 Base64 格式的 IR 碼

#### RF 碼（僅限 RM Pro / RM4 Pro）

1. 在 Home Assistant 中進入 **開發者工具 > 服務**
2. 呼叫 `remote.learn_command` 服務，並設定 `command_type: rf`
3. **頻率掃描**：長按遙控器按鈕，直到設備發出提示音（掃描 RF 頻率）
4. **碼學習**：短按遙控器按鈕以學習具體的指令碼
5. 學習到的 RF 碼同樣為 `b64:` 格式，可直接使用

**需要學習的按鈕：**
- T-UP：上簾邊往上
- T-DN：上簾邊往下
- B-UP：下簾邊往上
- B-DN：下簾邊往下
- STOP：停止

## 安裝方式

### 方式一：透過 HACS 安裝（推薦）

1. 確保已安裝 [HACS](https://hacs.xyz/)
2. 在 HACS 中點擊右上角的三個點選單
3. 選擇 **自訂存放庫（Custom repositories）**
4. 輸入此存放庫網址，類別選擇 **Integration**
5. 點擊 **新增**
6. 在 HACS 整合頁面搜尋 **IR Honeycomb Blind** 並安裝
7. 重新啟動 Home Assistant

### 方式二：手動安裝

1. 下載此存放庫的最新版本
2. 將 `custom_components/ir_honeycomb_blind` 資料夾複製到你的 Home Assistant 設定目錄下的 `custom_components` 資料夾中
   ```
   <config_dir>/
   └── custom_components/
       └── ir_honeycomb_blind/
           ├── __init__.py
           ├── manifest.json
           ├── config_flow.py
           ├── cover.py
           ├── sensor.py
           ├── binary_sensor.py
           ├── button.py
           ├── coordinator.py
           ├── const.py
           ├── strings.json
           ├── services.yaml
           ├── hacs.json
           └── translations/
               ├── en.json
               └── zh-Hant.json
   ```
3. 重新啟動 Home Assistant

## 設定方式

1. 前往 **設定 > 裝置與服務 > 新增整合**
2. 搜尋 **IR Honeycomb Blind**
3. 填寫設定表單：

| 欄位 | 說明 |
|------|------|
| 窗簾名稱 | 為此窗簾取一個獨特的名稱 |
| Broadlink 遙控器 | 選擇要使用的 Broadlink remote 實體 |
| IR 碼 (T-UP/T-DN/B-UP/B-DN/STOP) | 貼上 Base64 格式的 IR 碼，需以 `b64:` 開頭 |
| 全開時間 | 窗簾從全關到全開所需秒數 |
| 全關時間 | 窗簾從全開到全關所需秒數 |
| IR 重複次數 | 每次指令重複發送的次數（建議 3） |
| IR 重複間隔 | 重複發送之間的間隔秒數（建議 0.3） |
| 防抖延遲 | 等待使用者操作穩定的時間（建議 1.0） |
| 即時位置更新 | 移動中即時顯示估算位置 |
| 分離式位置/比例控制 | 建立分離的 Position 和 Ratio 窗簾實體 |
| 單一窗簾（含傾斜控制） | 建立單一窗簾實體，使用 Position + Tilt |

4. 點擊 **提交** 完成設定

## 校正功能

### 方式一：使用校正按鈕（推薦）

每組窗簾設定後會自動產生一個 **校正按鈕**（`button.xxx_calibrate`）：

1. 在 Home Assistant 儀表板或裝置頁面找到校正按鈕
2. 直接點擊按鈕即可執行校正
3. 校正完成後，位置會重設為：POS=0, R=0（全開狀態）

### 方式二：呼叫服務

透過 **開發者工具 > 服務** 呼叫 `ir_honeycomb_blind.calibrate`：

**參數：**
- `entry_id`（選填）：指定要校正的窗簾設定 ID。留空則校正所有窗簾。

### 使用時機

- 首次安裝後
- 位置追蹤不準確時
- 手動操作遙控器後

## 疑難排解

### IR 指令沒有反應
- 確認 Broadlink 設備已正確設定並在線上
- 確認 IR 碼格式正確（需以 `b64:` 開頭）
- 嘗試增加 IR 重複次數
- 確認紅外線傳輸器與窗簾之間沒有障礙物

### 位置不準確
- 重新測量全開/全關時間，確保數值準確
- 按下校正按鈕重設位置
- 避免手動使用遙控器（會導致追蹤偏差）

### 多個窗簾互相干擾
- 確認每組窗簾使用不同的 IR 碼
- 如果共用同一台 Broadlink，IR 指令會自動排隊，請耐心等待

## 授權

MIT License
