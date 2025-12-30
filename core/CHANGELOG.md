# Changelog

## [0.8.0](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.7.3...charmarr-lib-core-v0.8.0) (2025-12-30)


### Features

* **core:** adds a hardware mount reconciler ([4c979c1](https://github.com/charmarr/charmarr-lib/commit/4c979c18b2df256247cd6d9919addfd8834cf319))

## [0.7.3](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.7.2...charmarr-lib-core-v0.7.3) (2025-12-30)


### Bug Fixes

* **core:** fixes recyclarrs quirky template formats ([025693a](https://github.com/charmarr/charmarr-lib/commit/025693ae0129889cb3bb21da6f3ccf0148183f94))

## [0.7.2](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.7.1...charmarr-lib-core-v0.7.2) (2025-12-30)


### Bug Fixes

* **core:** use series profiles in recyclarr for sonarr ([c3275da](https://github.com/charmarr/charmarr-lib/commit/c3275da0efe767ff6601fc40754b02694b192043))

## [0.7.1](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.7.0...charmarr-lib-core-v0.7.1) (2025-12-30)


### Bug Fixes

* **core:** abstract common interface patterns into a base inbterface class and mixin ([8532d2f](https://github.com/charmarr/charmarr-lib/commit/8532d2fbb40751626be895080f3528516bb03a7b))

## [0.7.0](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.6.1...charmarr-lib-core-v0.7.0) (2025-12-30)


### Features

* **core:** add recyclarr abstractions ([4a86d54](https://github.com/charmarr/charmarr-lib/commit/4a86d54a338bc6f09eaa1ab591ceea084117ccc2))
* **core:** adds a shared config reconciler for arrs ([ab5ff46](https://github.com/charmarr/charmarr-lib/commit/ab5ff46d47ec17aba2634efea3acbd2e8a04c413))
* **core:** adds flaresolverr interface ([0fa35a7](https://github.com/charmarr/charmarr-lib/commit/0fa35a79af5d49a0bc2a1bce979143151267cdeb))
* **core:** adds media indexer abstractions ([eb04ea1](https://github.com/charmarr/charmarr-lib/commit/eb04ea1d236032dc5f941d3540cdc373272fd389))


### Bug Fixes

* **core:** fix recyclarr dotnet globalization ([07c49fc](https://github.com/charmarr/charmarr-lib/commit/07c49fc60d0c1708d6a0f0c21fc630f7d7b2fa2a))
* **core:** handles recyclarr as a side car ([dc708f2](https://github.com/charmarr/charmarr-lib/commit/dc708f22ce2d8f3c6e7d1efde4d38b71192cfc68))
* **core:** makes arr reconcilers resilient to failures ([6df6a0c](https://github.com/charmarr/charmarr-lib/commit/6df6a0c8015c93f88e946947eccbb3c7bfbd720a))
* **core:** recyclarr exten PATH with bin ([c248800](https://github.com/charmarr/charmarr-lib/commit/c248800914701b42d6148b93e4f6cc5c85e31c28))

## [0.6.1](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.6.0...charmarr-lib-core-v0.6.1) (2025-12-26)


### Bug Fixes

* **core:** minor structural changes for better maintainability ([851b0d2](https://github.com/charmarr/charmarr-lib/commit/851b0d2fb4433351618f78b095a48d38334c524c))

## [0.6.0](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.5.0...charmarr-lib-core-v0.6.0) (2025-12-26)


### Features

* **core:** adds a shared secret roation handler ([e3e2270](https://github.com/charmarr/charmarr-lib/commit/e3e2270d1127def8d6e48bc077284aac2784b69d))

## [0.5.0](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.4.2...charmarr-lib-core-v0.5.0) (2025-12-26)


### Features

* **core:** adds user reconciling for linusserverio images ([e86f7ea](https://github.com/charmarr/charmarr-lib/commit/e86f7eab38fca913039c64e533da46a0b2e7513a))

## [0.4.2](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.4.1...charmarr-lib-core-v0.4.2) (2025-12-26)


### Bug Fixes

* **core:** minimizes security ctx patching to fsGroup to reduce invasiveness ([25e4e06](https://github.com/charmarr/charmarr-lib/commit/25e4e0636b45b7062a2782d7ef0eb4b2da344a9c))

## [0.4.1](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.4.0...charmarr-lib-core-v0.4.1) (2025-12-26)


### Bug Fixes

* **core:** remove orphaned security ctx whens torage relation is removed ([d4e4735](https://github.com/charmarr/charmarr-lib/commit/d4e473548afff6364942d984ad3f5eb4d128a8a9))

## [0.4.0](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.3.2...charmarr-lib-core-v0.4.0) (2025-12-26)


### Features

* **core:** storage patching patches security ctx to replace s6 init layer ([087124a](https://github.com/charmarr/charmarr-lib/commit/087124a7a68ee908e7b31cdbc9cacc528ce50782))

## [0.3.2](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.3.1...charmarr-lib-core-v0.3.2) (2025-12-24)


### Bug Fixes

* **core:** code refactor and cleanup ([7b5e2e0](https://github.com/charmarr/charmarr-lib/commit/7b5e2e08d847d847ed57dbc92b5c8f9868ab3c1a))

## [0.3.1](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.3.0...charmarr-lib-core-v0.3.1) (2025-12-22)


### Bug Fixes

* **core:** fixes lightkube imports ([1c71cb5](https://github.com/charmarr/charmarr-lib/commit/1c71cb51d2fc750a842941d5bcae0116ca3febe0))
* **core:** formatting ([a8b2d25](https://github.com/charmarr/charmarr-lib/commit/a8b2d253069cebc9791a7ba6a45211374f6156e5))
* **core:** storage reconciler handles pvc removal ([6968a41](https://github.com/charmarr/charmarr-lib/commit/6968a41634d59f12d59da5371c31df598f349ed7))
* **testing:** adds trust to juju deploy ([e4ef13b](https://github.com/charmarr/charmarr-lib/commit/e4ef13b5bc5eba172cc6497b9a588081811149ed))

## [0.3.0](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.2.5...charmarr-lib-core-v0.3.0) (2025-12-17)


### Features

* **core:** adds a central reconciler ([4c2810e](https://github.com/charmarr/charmarr-lib/commit/4c2810e442eab4f5da19ea81eda0d14a931c57f6))

## [0.2.5](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.2.4...charmarr-lib-core-v0.2.5) (2025-12-16)


### Bug Fixes

* **core:** fixes local version file update ([06cffbc](https://github.com/charmarr/charmarr-lib/commit/06cffbcc2593059591b1e51266954c8352097b45))

## [0.2.4](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.2.3...charmarr-lib-core-v0.2.4) (2025-12-16)


### Bug Fixes

* **core:** fix build path for release wf ([b61be60](https://github.com/charmarr/charmarr-lib/commit/b61be60d26f823681ea3b6d6754b99e5b529be9e))

## [0.2.3](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.2.2...charmarr-lib-core-v0.2.3) (2025-12-16)


### Bug Fixes

* **core:** uses inline publish to workaround pypi restrictions ([64f540e](https://github.com/charmarr/charmarr-lib/commit/64f540ec4f4be74934202aa7aac55450817b2e7e))

## [0.2.2](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.2.1...charmarr-lib-core-v0.2.2) (2025-12-16)


### Bug Fixes

* **core:** fixes release to pypi ([a18e847](https://github.com/charmarr/charmarr-lib/commit/a18e8475719b5f7d250050aca6d19cd23e9a97da))

## [0.2.1](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.2.0...charmarr-lib-core-v0.2.1) (2025-12-16)


### Bug Fixes

* **core:** fixes release please process ([c1c9c37](https://github.com/charmarr/charmarr-lib/commit/c1c9c3708a2a391a6b5807b8b3b5d88632fcb386))

## [0.2.0](https://github.com/charmarr/charmarr-lib/compare/charmarr-lib-core-v0.1.0...charmarr-lib-core-v0.2.0) (2025-12-15)


### Features

* adds arr specific http clients for core lib ([3d4af88](https://github.com/charmarr/charmarr-lib/commit/3d4af88807daf5d92be0146024f7d8863160eaa4))
* adds base http client class for core lib ([133e484](https://github.com/charmarr/charmarr-lib/commit/133e484e8127d3b99097d1c4819106c3c066573e))
* adds dev envs for charmarr lib packages ([b8ee5b2](https://github.com/charmarr/charmarr-lib/commit/b8ee5b29bf07a9c4e53a5443da3742c62ec4191c))
* adds download client interfaces ([c638bb2](https://github.com/charmarr/charmarr-lib/commit/c638bb2ccbaafce8ecd2cf4396104f7712c5c770))
* adds media indexer interfaces ([58c1304](https://github.com/charmarr/charmarr-lib/commit/58c1304143662c2b24deef5c153812dff27c8360))
* adds media manager core lib ([d82a7fd](https://github.com/charmarr/charmarr-lib/commit/d82a7fdb3450082493f547f32f8d6303a26bbc0d))
* adds media storage core lib ([757cb6d](https://github.com/charmarr/charmarr-lib/commit/757cb6d9be13217e36057752cabe6bf2c9cc3174))
* adds payload builders for arr calls in core lib ([3a09022](https://github.com/charmarr/charmarr-lib/commit/3a09022277b85d7b1a7e9589eced15f674d1d7d2))
* scaffolds monorepo with required packages ([eca8d38](https://github.com/charmarr/charmarr-lib/commit/eca8d38bec8f03dcabd4363b84e1743e495fed4c))
