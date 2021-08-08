# Changelog

All notable changes to this project will be documented in this file.

## [0.7.0] - 2021-08-08 

This is a major change and is not backwards compatible in our quest to reach 1.0 status.

### Added

- Generic class for containers (Devices/Brain)
- Base class for Device inheritance (DeviceTemplate)
- getIPAddress() for identifying IP of network interfaces
- Base support for PyQt5 forms via karen-panel

### Modified

- Separated features into separate packages
- Rewritten brain/container communications using "accepts"
- Moved Streaming Client into karen.shared
- Defaulting containers to interface IP rather than just localhost
- Documentation updated to reflect new patterns

### Removed

- Separated features into separate packages
- See karen-brain, karen-device, karen-watcher, karen-listener, karen-speaker

## [0.6.0] - 2021-07-02

### Added

- Added Watcher device
- Trainer for watcher device using haarcascade classifiers
- Basic Configuration for Video + Audio (basic_config_video.json)
- Handlers for capturing IMAGE_INPUT
- Context object for handlers and devices

### Modified

- karen.start() method to support "video" option
- Fixed eval issues in startup
- Updated Raspberry Pi documentation
- Improved device management via control panel

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

- Multiple daemons 
- Basic support for microphone devices (via mozilla.deepspeech)
- Basic support for camera devices (via opencv2)
- Web console

### Changed

- Startup routines

### Removed

- Unnecessary setup tasks
