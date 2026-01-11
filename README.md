 
# Xiaomi IR Climate (UI Version)

A custom Home Assistant integration for controlling air conditioners via Xiaomi IR Remotes (Chuangmi/Miot). 

**🚀 Now featuring a full UI Config Flow & Magic Auto-Learning!** No more editing complex YAML files. You can now set up your AC and learn IR codes directly from the Home Assistant interface.

## ✨ Features
* **100% UI Configuration:** Set up your climate entity, min/max temps, and supported modes via the Integrations page.
* **Magic Auto-Learning:** The integration listens for the Xiaomi "learned code" notification and **automatically fills the IR code** for you.
* **Unified Editor:** Trigger learning, capture codes, and save them all from a single screen.
* **Smart Defaults:** Remembers your last used Mode/Fan/Temp so you can quickly map out your entire remote control.

## 📦 Installation

1.  Download this repository.
2.  Copy the `xiaomi_ir_climate` folder into your Home Assistant `custom_components` directory.
    * Path: `/config/custom_components/xiaomi_ir_climate/`
3.  **Restart Home Assistant**.

## ⚙️ Setup

1.  Go to **Settings** > **Devices & Services**.
2.  Click **+ ADD INTEGRATION**.
3.  Search for **Xiaomi IR Climate (UI)**.
4.  Fill in the basic details:
    * **Name:** e.g., "Bedroom AC"
    * **Remote Entity:** Select your Xiaomi remote (e.g., `remote.xiaomi_miio_...`).
    * **Min/Max Temp:** Set the range your AC supports (e.g., 16-30).
    * **Modes:** Select the HVAC and Fan modes your AC supports.
5.  Click **Submit**.

## 🎮 How to Learn Codes (The Easy Way)

Once the entity is created, you need to teach it the IR codes for your specific AC.

1.  Go to **Settings** > **Devices & Services** > **Xiaomi IR Climate**.
2.  Click the **CONFIGURE** button on the integration entry.
3.  **Select the State:** Choose the combination you want to learn (e.g., **Cool**, **24°C**, **Auto Fan**).
4.  **Check the Box:** ☑️ `Trigger Remote Learning`.
5.  Click **Submit**.
6.  **Point & Shoot:**
    * The form will go into a "Loading" state.
    * Your Xiaomi Remote usually beeps (indicating learning mode).
    * Point your physical AC remote at the Xiaomi device and press the corresponding button (Cool 24° Auto).
7.  **Auto-Fill Magic:**
    * The integration will detect the code from the notification.
    * The screen will reload with the **IR Code automatically filled in**.
8.  **Save:** Click **Submit** again to save that code to the database.

> **Pro Tip:** The form remembers your last setting. After saving "Cool 24°", it will reopen on "Cool". You just need to change the temp to "25°", check "Trigger Learning", and repeat!

## 🛠 Troubleshooting

* **"Call Failed" Error:** This usually means the integration couldn't talk to your remote. Ensure your `remote.xiaomi_...` entity is available and working.
* **Timeout / Code not filling:**
    * Ensure you press the remote button within 30 seconds.
    * Check your Home Assistant **Notifications** (Bell icon). If the code appears there but didn't auto-fill, the format might be unique.
    * You can always manually copy the code from the notification and paste it into the "IR Code" box.

---
*Based on the original work by [Anonym-tsk](https://github.com/Anonym-tsk).*
