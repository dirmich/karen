# Calling the start() method
There are lots of ways to leverage karen.  You can import the device modules like listener and use on its own or you can start the entire process.  There is a [basic configuration](config.example.md) file located in the data directory inside the karen module directory (```/path/to/karen/data/basic_config.json```).

To run Karen in the entirety:

```
import karen
karen.start('/path/to/config.json')
```

If you omit the configuration file then Karen will start with the [basic configuration example](config.example.md).

**NOTICE** - Karen is under development against Python 3.  She is not compatible with Python 2 so be sure to use ```pip3``` or ```python3``` if appropriate (and install the related binaries if needed).


# karen.start

::: karen.start
    rendering:
      show_source: false