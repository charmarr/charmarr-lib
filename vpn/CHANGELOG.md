# Changelog

## [0.3.0](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-vpn-v0.2.2...charmarr-lib-vpn-v0.3.0) (2025-12-24)


### Features

* **vpn:** adds configmap reconciler ([0e8acef](https://github.com/charmarr/charmarr-lib/commit/0e8acefe727edc22cd27110d62346cff1c8f4719))
* **vpn:** removes pod gateway clients when called with None ([b194d75](https://github.com/charmarr/charmarr-lib/commit/b194d75dc7a8c6894694b15f5e99a40200b17141))


### Bug Fixes

* **vpn:** fix networkpolicy import ([db067e3](https://github.com/charmarr/charmarr-lib/commit/db067e34dde4dac972cb2e08a61462bda23e3ff9))
* **vpn:** fixes lightkube data types ([f48c112](https://github.com/charmarr/charmarr-lib/commit/f48c112081e7f5ee8d13d65c5355d501c6460ae9))
* **vpn:** force patch pod gateway to sync with juju config changes ([acbe049](https://github.com/charmarr/charmarr-lib/commit/acbe04971fdb0262d1f5159bdc4ebbedca81b16b))
* **vpn:** forces comma separate cidr blocks ([d2eff2b](https://github.com/charmarr/charmarr-lib/commit/d2eff2be672f28bdb5216b7a6121fa0169998a5d))
* **vpn:** gateway settings are mounted through a configmap ([372395f](https://github.com/charmarr/charmarr-lib/commit/372395f00be3624b162a1559ba5d1f681b27e3c7))
* **vpn:** lets patcher handler differences instead of catching 0 diff ([a0463db](https://github.com/charmarr/charmarr-lib/commit/a0463dba8235def17d0ecd587f552899da23cdf1))
* **vpn:** makes input cidr whitelisting optional ([7a089a2](https://github.com/charmarr/charmarr-lib/commit/7a089a2c49dd87a6e7e1448761f4d263509fdd7f))
* **vpn:** use vxlan-id from relation data for gateway client ([f495f9f](https://github.com/charmarr/charmarr-lib/commit/f495f9f30d0b70912d11e21f3a21722e51eafb7b))

## [0.2.2](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-vpn-v0.2.1...charmarr-lib-vpn-v0.2.2) (2025-12-16)


### Bug Fixes

* **vpn:** fixes local version file update ([c4b5ce2](https://github.com/charmarr/charmarr-lib/commit/c4b5ce27825522ff07aee1e194755ced42401f8c))

## [0.2.1](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-vpn-v0.2.0...charmarr-lib-vpn-v0.2.1) (2025-12-16)


### Bug Fixes

* **vpn:** fixes release please process ([72c0ea3](https://github.com/charmarr/charmarr-lib/commit/72c0ea3998188b96b74445e7076ac9e0ac5cebd2))

## [0.2.0](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-vpn-v0.1.0...charmarr-lib-vpn-v0.2.0) (2025-12-15)


### Features

* adds dev envs for charmarr lib packages ([b8ee5b2](https://github.com/charmarr/charmarr-lib/commit/b8ee5b29bf07a9c4e53a5443da3742c62ec4191c))
* scaffolds monorepo with required packages ([eca8d38](https://github.com/charmarr/charmarr-lib/commit/eca8d38bec8f03dcabd4363b84e1743e495fed4c))
