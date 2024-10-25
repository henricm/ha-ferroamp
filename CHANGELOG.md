# Changelog

## [1.15.0](https://github.com/henricm/ha-ferroamp/compare/v1.14.2...v1.15.0) (2024-10-25)


### Features

* **changelog:** add custom sections for changelog types ([35112a4](https://github.com/henricm/ha-ferroamp/commit/35112a4d613bb753c7abbbd830cc8b22d32e2e3f))


### Bug Fixes

* correct config filename ([aa99106](https://github.com/henricm/ha-ferroamp/commit/aa991061fb6642427e266d371d3dd9493ea8b77b))
* revert version update from failed release ([37fe28a](https://github.com/henricm/ha-ferroamp/commit/37fe28ae192df0ec425ad95429de65dd99068450))
* update branch from main to master in workflow ([3fe52b7](https://github.com/henricm/ha-ferroamp/commit/3fe52b71e8e9887ff838486d71c20359bda45a25))


### Documentation

* add changelog for releases up to 1.14.2 ([d6e4375](https://github.com/henricm/ha-ferroamp/commit/d6e43752f74d7e5aada026ebdb9a956a3edb6125))


### Miscellaneous Chores

* await hass.config_entries.async_forward_entry_setups ([3874c96](https://github.com/henricm/ha-ferroamp/commit/3874c9653ab4334396f28e146786f65a2d694b16))
* **release:** vnull [skip ci] ([ca9a147](https://github.com/henricm/ha-ferroamp/commit/ca9a147efafbe87d77c30421e919452e17739216))


### Build System

* **deps-dev:** bump black from 24.4.2 to 24.8.0 ([8486f13](https://github.com/henricm/ha-ferroamp/commit/8486f1325c6d4f55f43ec0cbfae308955dc22c81))
* **deps-dev:** bump black from 24.8.0 to 24.10.0 ([4a2f7dd](https://github.com/henricm/ha-ferroamp/commit/4a2f7ddf5c42f8f007e55304047530e2308f19e8))
* **deps-dev:** bump flake8 from 7.1.0 to 7.1.1 ([152596b](https://github.com/henricm/ha-ferroamp/commit/152596b2139bb9b192a2a106c3de67aa968102a9))
* **deps-dev:** bump pre-commit from 3.7.1 to 3.8.0 ([6adcf5a](https://github.com/henricm/ha-ferroamp/commit/6adcf5ad83e8ca6500ca9c60f073c55f3eb931b6))
* **deps-dev:** bump pre-commit from 3.8.0 to 4.0.0 ([adae2e9](https://github.com/henricm/ha-ferroamp/commit/adae2e97a5a436a99128e6c90e5fdd573233eb16))
* **deps-dev:** bump pre-commit from 4.0.0 to 4.0.1 ([45aef48](https://github.com/henricm/ha-ferroamp/commit/45aef4887434c47b671097a8d8a2cfd516e25285))


### Continuous Integration

* add conventional changelog configuration ([f1ef076](https://github.com/henricm/ha-ferroamp/commit/f1ef076e2a2e3355c58ac6c92677a3065d478045))
* migrate to release-please flow ([7583cf1](https://github.com/henricm/ha-ferroamp/commit/7583cf15c76202a78f547e034ce73cf753c65fc4))
* set Python version in pre-commit GitHub workflow ([ef63777](https://github.com/henricm/ha-ferroamp/commit/ef63777ff2e6aa7f5fcdc02c2e3418c5819ee87e))

## [1.14.2] - 2024-07-03

### Bug Fixes

- Commitlint config
- Use async_unload from hass.config_entries
- Add wait_background_tasks parameter to block_till_done function
- Ignore lingering timer tests for now
- Update fault code attributes keys to strings
- Replace deprecated constants

### Miscellaneous Tasks

- Update to 3.12 plus some fixes
- Await hass.async_create_task
- *(release)* V1.14.2 [skip ci]

### Build

- *(deps-dev)* Bump black from 23.12.1 to 24.1.1
- *(deps)* Bump pre-commit/action from 3.0.0 to 3.0.1
- *(deps-dev)* Bump pre-commit from 3.6.0 to 3.6.1
- *(deps-dev)* Bump black from 24.1.1 to 24.2.0
- *(deps-dev)* Bump pre-commit from 3.6.1 to 3.6.2
- *(deps-dev)* Bump black from 24.2.0 to 24.3.0
- *(deps-dev)* Bump pre-commit from 3.6.2 to 3.7.0
- *(deps)* Bump wagoid/commitlint-github-action from 5 to 6
- *(deps-dev)* Bump black from 24.3.0 to 24.4.0
- *(deps-dev)* Bump black from 24.4.0 to 24.4.1
- *(deps-dev)* Bump black from 24.4.1 to 24.4.2
- *(deps-dev)* Bump pre-commit from 3.7.0 to 3.7.1
- *(deps)* Bump pytest-homeassistant-custom-component
- *(deps-dev)* Bump flake8 from 7.0.0 to 7.1.0

## [1.14.1] - 2024-01-17

### Bug Fixes

- Add name to service fields
- Handle new field preview in config in HA 2023.9
- Ignore minor_version in config flow test
- *(sensor)* Do not log warning if sensor is not present

### Miscellaneous Tasks

- *(pre-commit-hooks)* Add some checks, fix requirements files
- *(devcontainer)* Remove deprecated settings
- *(devcontainer)* Add yaml extension
- *(devcontainer)* Fix pylance not picking up correct interpreter
- *(pre-commit-hooks)* Add commitlint pre-commit hook
- *(ide)* Fix max-line-width for flake8 to same as black and isort
- *(devcontainer)* Open HA in browser automatically
- *(docs)* Add mqtt integration link and fix typo
- Fix race condition in postCreateCommand
- Add wait option to debug configuration
- *(vscode)* Prompt for remote debug host
- *(release)* V1.14.1 [skip ci]

### Build

- *(deps-dev)* Bump pre-commit from 3.3.3 to 3.4.0
- *(deps)* Bump actions/checkout from 3 to 4
- *(deps-dev)* Bump black from 23.7.0 to 23.9.1
- *(deps-dev)* Bump pre-commit from 3.4.0 to 3.5.0
- *(deps-dev)* Bump black from 23.9.1 to 23.10.0
- *(deps-dev)* Bump black from 23.10.0 to 23.10.1
- *(deps-dev)* Bump black from 23.10.1 to 23.11.0
- *(deps)* Bump actions/setup-python from 4 to 5
- *(deps-dev)* Bump isort from 5.12.0 to 5.13.0
- *(deps-dev)* Bump pre-commit from 3.5.0 to 3.6.0
- *(deps-dev)* Bump isort from 5.13.0 to 5.13.1
- *(deps-dev)* Bump black from 23.11.0 to 23.12.0
- *(deps-dev)* Bump isort from 5.13.1 to 5.13.2
- *(deps)* Bump github/codeql-action from 2 to 3
- *(deps-dev)* Bump black from 23.12.0 to 23.12.1
- *(deps)* Bump TriPSs/conventional-changelog-action from 4 to 5
- *(deps-dev)* Bump flake8 from 6.1.0 to 7.0.0

## [1.14.0] - 2023-08-17

### Features

- Vscode devcontainer configuration
- *(ci)* Add github action to run pre-commit
- Remove precision config since now builtin to HA

### Bug Fixes

- Enforce codestyle
- Reformat code using pre-commit configuration
- *(devcontainer)* Install pre-commit hooks
- *(docs)* Update contribute guidelines

### Miscellaneous Tasks

- Add name to services
- Update minimum HA version and bump python to 3.11
- *(release)* V1.14.0 [skip ci]

### Build

- *(deps-dev)* Bump flake8 from 6.0.0 to 6.1.0
- *(deps)* Bump actions/setup-python from 3 to 4
- *(deps)* Bump TriPSs/conventional-changelog-action from 3 to 4

## [1.13.0] - 2023-07-26

### Features

- Add separate entities per phase

### Bug Fixes

- Capitalization of sensors

### Miscellaneous Tasks

- *(release)* V1.13.0 [skip ci]

### Build

- *(deps)* Bump actions/setup-python from 4.6.1 to 4.7.0

## [1.12.5] - 2023-07-08

### Bug Fixes

- Correct calculation dc link voltage sensor state

### Miscellaneous Tasks

- *(release)* V1.12.5 [skip ci]

## [1.12.4] - 2023-07-07

### Bug Fixes

- Add additional SSO fault codes

### Documentation

- Adding how to monitor latest version of ferroamp to readme.md
- Adding how to monitor latest version of ferroamp to readme.md
- Adding how to monitor latest version of ferroamp to readme.md
- Increasing scan interval for version scraper in README.md
- Bugfix on automation to trigger new ferroamp version

### Miscellaneous Tasks

- *(release)* V1.12.4 [skip ci]

### Build

- *(deps)* Bump actions/setup-python from 4.6.0 to 4.6.1

## [1.12.3] - 2023-05-02

### Bug Fixes

- Ignore unknown last state

### Miscellaneous Tasks

- *(release)* V1.12.3 [skip ci]

## [1.12.2] - 2023-04-24

### Bug Fixes

- Only create battery specific sensors if present in message from EnergyHub

### Miscellaneous Tasks

- *(release)* V1.12.2 [skip ci]

### Build

- *(deps)* Bump actions/setup-python from 4.5.0 to 4.6.0

## [1.12.1] - 2023-04-15

### Bug Fixes

- Add control status sensor on init

### Miscellaneous Tasks

- *(release)* V1.12.1 [skip ci]

## [1.12.0] - 2023-04-05

### Features

- Added possibility to turn on debug logging of events

### Miscellaneous Tasks

- *(release)* V1.12.0 [skip ci]

## [1.11.2] - 2023-04-05

### Bug Fixes

- Wait for HASS to complete
- Don't store events if sensor is not present
- Ignore zero values for total-increasing energy sensors

### Miscellaneous Tasks

- *(release)* V1.11.2 [skip ci]

## [1.11.1] - 2023-03-21

### Bug Fixes

- Make sure old fault codes gets cleared

### Miscellaneous Tasks

- *(release)* V1.11.1 [skip ci]

## [1.11.0] - 2023-03-18

### Features

- Only add sensors for loadbalancing if present in message

### Miscellaneous Tasks

- Update config to extend config-conventional
- Add contribution info to readme
- *(release)* V1.11.0 [skip ci]

## [1.10.2] - 2023-03-09

### Bug Fixes

- Support for energy counter being reset

### Miscellaneous Tasks

- Add python 3.11 to test matrix
- Remove python 3.11 from test matrix since not supported by HA yet
- Drop support for Python 3.9 since HA no longer supports it
- Replace deprecated release action
- Sort manifest attributes
- *(release)* V1.10.2 [skip ci]

### Build

- *(deps)* Bump actions/setup-python from 4.3.1 to 4.4.0
- *(deps)* Bump actions/setup-python from 4.4.0 to 4.5.0

## [1.10.1] - 2022-12-19

### Bug Fixes

- Log warn in case of multiple integration entries

### Miscellaneous Tasks

- Run build and test on PRs
- *(release)* V1.10.1 [skip ci]

## [1.10.0] - 2022-12-12

### Features

- Updating readme.md
- Make sure MQTT integration is loaded before setup

### Bug Fixes

- Ignore context in assertion
- Handle asyncio correctly in tests

### Miscellaneous Tasks

- Allow longer body-lines for all commits and remove node-dependency
- Use new enums for energy, power and temperature
- *(release)* V1.10.0 [skip ci]

### Build

- *(deps)* Bump actions/setup-python from 4.2.0 to 4.3.0
- *(deps)* Bump actions/setup-python from 4.3.0 to 4.3.1
- *(deps)* Bump pytest-homeassistant-custom-component

## [1.9.0] - 2022-08-09

### Features

- Requirements for hacs default
- Change name for hacs.yaml

### Miscellaneous Tasks

- *(release)* V1.9.0 [skip ci]

## [1.8.0] - 2022-08-08

### Features

- Migrate to new entity naming style

### Miscellaneous Tasks

- *(release)* V1.8.0 [skip ci]

### Build

- *(deps)* Bump actions/setup-python from 4.1.0 to 4.2.0

## [1.7.5] - 2022-07-25

### Bug Fixes

- Battery icon not shown when below 10 percent

### Miscellaneous Tasks

- Add minimal package.json to get commitlint to run correctly
- Add python 3.10 to package workflow
- *(release)* V1.7.5 [skip ci]

### Build

- *(deps)* Bump actions/setup-python from 3.1.2 to 4.0.0
- *(deps)* Bump wagoid/commitlint-github-action from 4 to 5
- *(deps)* Bump actions/setup-node from 2 to 3
- *(deps)* Bump actions/setup-python from 4.0.0 to 4.1.0

## [1.7.4] - 2022-06-02

### Bug Fixes

- Change usage of deprecated methods

### Miscellaneous Tasks

- *(release)* V1.7.4 [skip ci]

### Build

- *(deps)* Bump pytest-homeassistant-custom-component

## [1.7.3] - 2022-05-04

### Bug Fixes

- Handle unknown value for percentage sensor
- Make four more sensors total increasing

### Miscellaneous Tasks

- *(release)* V1.7.3

### Build

- *(deps)* Bump actions/setup-python from 3.1.0 to 3.1.1
- *(deps)* Bump actions/setup-python from 3.1.1 to 3.1.2
- *(deps)* Bump github/codeql-action from 1 to 2

## [1.7.2] - 2022-04-05

### Bug Fixes

- Set native unit of measurement since that seems to be required in HA 2022.4

### Miscellaneous Tasks

- *(release)* V1.7.2

### Build

- *(deps)* Bump actions/setup-python from 2 to 3.1.0
- *(deps)* Bump pytest-homeassistant-custom-component

## [1.7.1] - 2022-03-17

### Bug Fixes

- Mark sensor as added to HASS even if no existing state is found

### Miscellaneous Tasks

- *(release)* V1.7.1

### Build

- *(deps)* Bump actions/checkout from 2 to 3
- *(deps)* Bump pytest-homeassistant-custom-component

## [1.7.0] - 2022-02-21

### Features

- Make sure that 3-phase energy sensors are strictly increasing

### Bug Fixes

- Failing tests due to blocking calls

### Miscellaneous Tasks

- Update to use sensor enums for device and state class
- *(release)* V1.7.0

### Build

- *(deps)* Bump pytest-homeassistant-custom-component

## [1.6.0] - 2021-12-08

### Features

- Updated to support Home Assistant 2021.12

### Miscellaneous Tasks

- *(release)* V1.6.0

### Build

- *(deps)* Bump pytest-homeassistant-custom-component

## [1.5.0] - 2021-12-04

### Features

- Add sensor for load balancing

### Miscellaneous Tasks

- *(release)* V1.5.0

## [1.4.2] - 2021-11-21

### Bug Fixes

- Make relay status history available

### Miscellaneous Tasks

- Add config for commitlint
- *(release)* V1.4.2

## [1.4.1] - 2021-11-05

### Bug Fixes

- Handle unknown value for energy sensor

### Miscellaneous Tasks

- Use DeviceInfo class
- *(release)* V1.4.1

### Build

- *(deps)* Bump pytest-homeassistant-custom-component
- *(deps)* Bump paho-mqtt from 1.5.1 to 1.6.0
- *(deps)* Bump paho-mqtt from 1.6.0 to 1.6.1
- *(deps)* Bump pytest-homeassistant-custom-component

## [1.4.0] - 2021-09-27

### Features

- Make sure state is always increasing for energy sensors

### Bug Fixes

- Handle missing values in a better way
- Average calculation

### Documentation

- How to setup the Energy Dashboard
- Add info on SSO setup
- Add info regarding battery system

### Miscellaneous Tasks

- *(release)* V1.4.0

### Build

- Use released version of pytest-homeassistant-custom-component
- Remove direct dependency on voluptous

## [1.3.0] - 2021-09-01

### Features

- Updated to support Home Assistant 2021.9 long term stats
- Add support for long-term statistics to SSO energy sensor

### Miscellaneous Tasks

- *(release)* V1.3.0

## [1.2.1] - 2021-08-28

### Bug Fixes

- Rename sensors for load balancing

### Miscellaneous Tasks

- Add Dependabot config
- Add commitlint action
- Remove dependency on homeassistant
- *(release)* V1.2.1

## [1.2.0] - 2021-08-09

### Features

- Add last_reset to battery energy sensors
- Remove integration name from sensor names

### Miscellaneous Tasks

- Update tests
- *(release)* V1.2.0

## [1.1.0] - 2021-08-05

### Features

- Add sensors used for load balancing applications.

### Bug Fixes

- Tests, imports and state-class

### Documentation

- Remove not about being work in progress since it's quite stable now

### Miscellaneous Tasks

- Update version
- *(release)* V1.1.0

## [1.0.0] - 2021-08-04

### Miscellaneous Tasks

- Revert version-update

## [1.0.0-beta] - 2021-08-03

### Features

- [**breaking**] Add support for Home Assistant Home Energy Management

### Miscellaneous Tasks

- Add support for beta-version when releasing from non-master
- Change exports
- *(release)* V1.0.0

## [0.1.1] - 2021-08-03

### Bug Fixes

- Only migrate ESM entities that actually need migrating

### Miscellaneous Tasks

- *(release)* V0.1.1

## [0.1.0] - 2021-07-27

### Features

- Update to HA 2021.7 and use entity attrs
- Add release workflow

### Miscellaneous Tasks

- Cleanup duplication in tests
- Move and rename constants
- Remove some duplication
- Set minimum HA version to 2021.6
- *(release)* V0.1.0

## [0.0.6] - 2021-07-08

### Features

- Trim ESM name to just serial number
- Add textual representation of ESO faultcodes as attributes
- Add SSO fault codes

### Bug Fixes

- Register version-sensor earlier and actually write state to HA

### Miscellaneous Tasks

- Remove logging of phases

## [0.0.5] - 2021-07-06

### Features

- Add missing ESM Rated Power sensor
- Add sensor for extapi version
- Remove model-info from SSO-name

### Bug Fixes

- Strip prefix in non python 3.9+ way

### Miscellaneous Tasks

- Add migration from old to new unique id
- Change Gitter-badge to one that is in the same style as the HACS-badge

## [0.0.4] - 2021-06-27

### Features

- Add missing sensor for Adaptive Current Equalization
- Add sensor for estimated grid frequency
- Change default precisions and make them configurable
- Add option for frequency precision
- Add ESM status sensor
- Add sensor for last command and status

### Bug Fixes

- Change link for Mosquitto bridge connections

### Miscellaneous Tasks

- Change unit of measurement for ESO and SSO power from kW to W
- Fix typo

## [0.0.3-beta] - 2021-05-24

### Features

- Add selectors to services and add tests

### Miscellaneous Tasks

- Add info on HACS-installation to readme
- Update README and HACS info

## [0.0.2] - 2021-05-24

### Miscellaneous Tasks

- Add github actions
- Add HACS-info

## [0.0.1] - 2021-05-20

### Features

- Add config and option flow, multiple hubs

### Miscellaneous Tasks

- Change to new directory structure to prepare for HACS installation

<!-- generated by git-cliff -->
