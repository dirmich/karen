# Changelog

All notable changes to this project will be documented in this file.

## [0.5.5] - 2021-06-19

### Added

- Download_model support to auto-detect deepspeech version and location
- Simplified startup logic with default configuration

### Modified 

- Install process for pypi (validated on Raspberry Pi)
- Docs now reflect simplified startup and relocated library paths
- Minimized dependencies/requirements list


## [0.5.4] - 2021-06-16

### Added

- Callback handlers for brain for extensible support
- Callback support for data capture and output devices for extensible support
- Listener daemon supports user-supplied callbacks for STT delivery
- Dynamic device loader allow for expansion of new input/output devices
- Python module setup and egg generation
- Unit Tests for listener
- Added mobile support for web gui
- Added configuration-based startup

### Changed

- Devices are now containerized in one TCP daemon
- Device and TCP daemon interactions now operate through callbacks
- Internal libraries have all changed and are not backwards compatible
- Moved location of webgui files
- Updated look-and-feel of web gui

### Removed

- Unnecessary setup tasks


## [0.4.1] - 2020-12-26

### Added

- Multiple daemons [@lnxusr](https://github.com/lnxusr1).
- Basic support for microphone devices (via mozilla.deepspeech)
- Basic support for camera devices (via opencv2)
- Web console

### Changed

- Startup routines

### Removed

- Unnecessary setup tasks
