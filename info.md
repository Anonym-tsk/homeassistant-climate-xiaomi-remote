## Xiaomi IR Climate

#### Requirements
[Xiaomi IR Remote](https://www.home-assistant.io/components/remote.xiaomi_miio/) component need to be enabled and configured

#### Configuration variables:
| Variable |  Required  | Description |
| -------- | ---------- | ----------- |
| `remote` | yes | **entity_id** of the Xiaomi IR Remote device |
| `commands` | yes | Commands list (see below) |
| `name` | no | Name of climate component |
| `temp_sensor` | no | **entity_id** for a temperature sensor, **temp_sensor.state must be temperature** |
| `power_template` | no | **template** that returns status of climete, **must returns boolean value** |
| `min_temp` | no | Set minimum available temperature (default: 16) |
| `max_temp` | no | Set maximum available temperature (default: 32) |
| `target_temp` | no | Set initial target temperature (default: 24) |
| `target_temp_step` | no | Set target temperature step (default: 1) |
| `hvac_mode` | no | Set initial default operation mode (default: off) |
| `fan_mode` | no | Set initial default fan mode (default: auto) |
| `customize`<br/>`- hvac_modes`<br/>`- fan_modes`<br/>`- preset_modes` | no | List of options to customize<br/>- List of operation modes (default: off, heat, cool, auto)<br/>- List of fan modes (default: low, medium, high, auto)<br/>- List of preset modes |

#### Basic Example:
```
climate:
  - platform: xiaomi_remote
    name: Air Conditioner
    remote: remote.xiaomi_miio_192_168_10_101
    commands: !include Roda-YKR-H-102E.yaml
```

#### Custom Example:
```
climate:
  - platform: xiaomi_remote
    name: Air Conditioner
    remote: remote.xiaomi_miio_192_168_10_101
    commands: !include Roda-YKR-H-102E.yaml
    temp_sensor: sensor.co2mon_temperature
    power_template: "{{ states('sensor.plug_power_158d0002366887') | float > 50 }}"
    min_temp: 16
    max_temp: 32
    target_temp: 24
    target_temp_step: 1
    hvac_mode: 'off'
    fan_mode: auto
    customize:
      hvac_modes:
        - 'off'
        - cool
        - heat
        - dry
        - fan_only
        - auto
      fan_modes:
        - low
        - medium
        - high
        - auto
      preset_modes:
        - eco
        - away
        - boost
        - comfort
        - home
        - sleep
```

#### How to make your configuration YAML file
* Use [`remote.xiaomi_miio_learn_command`](https://www.home-assistant.io/components/remote.xiaomi_miio/#remotexiaomi_miio_learn_command) to get commands from your remote.
* Create YAML file same as `Roda-YKR-H-102E.yaml` with your commands.
  * Required command `off` (`'off': <command>`)
  * Optional commands `presets/preset_mode` (`presets/'off': <command>`, `presets/eco: <command>`)
  * Optional commands: `operation/fan_mode/temperature` (available nesting: `operation/fan_mode/temperature`, `operation/fan_mode`, `operation`)
  * `'off'` commands must be in quotes

Example:
```
'off': <raw_command>
cool:
  low:
    16: <raw_command>
    17: <raw_command>
    ...
heat:
  low: <raw_command>
  high: <raw_command>
dry: <raw_command>
presets:
  'off': <raw_command>
  eco: <raw_command>
  sleep: <raw_command>
```

---

Enjoy my work? Help me out for a couple of :beers: or a :coffee:!

[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/qcDXvboAE)
