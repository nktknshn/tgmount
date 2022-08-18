```python
"""
    This is the abstract base class for the client. It defines some
    basic stuff like connecting, switching data center, etc, and
    leaves the `__call__` unimplemented.

    Arguments
        session (`str` | `telethon.sessions.abstract.Session`, `None`):
            The file name of the session file to be used if a string is
            given (it may be a full path), or the Session instance to be
            used otherwise. If it's `None`, the session will not be saved,
            and you should call :meth:`.log_out()` when you're done.

            Note that if you pass a string it will be a file in the current
            working directory, although you can also pass absolute paths.

            The session file contains enough information for you to login
            without re-sending the code, so if you have to enter the code
            more than once, maybe you're changing the working directory,
            renaming or removing the file, or using random names.

        api_id (`int` | `str`):
            The API ID you obtained from https://my.telegram.org.

        api_hash (`str`):
            The API hash you obtained from https://my.telegram.org.

        connection (`telethon.network.connection.common.Connection`, optional):
            The connection instance to be used when creating a new connection
            to the servers. It **must** be a type.

            Defaults to `telethon.network.connection.tcpfull.ConnectionTcpFull`.

        use_ipv6 (`bool`, optional):
            Whether to connect to the servers through IPv6 or not.
            By default this is `False` as IPv6 support is not
            too widespread yet.

        proxy (`tuple` | `list` | `dict`, optional):
            An iterable consisting of the proxy info. If `connection` is
            one of `MTProxy`, then it should contain MTProxy credentials:
            ``('hostname', port, 'secret')``. Otherwise, it's meant to store
            function parameters for PySocks, like ``(type, 'hostname', port)``.
            See https://github.com/Anorov/PySocks#usage-1 for more.

        local_addr (`str` | `tuple`, optional):
            Local host address (and port, optionally) used to bind the socket to locally.
            You only need to use this if you have multiple network cards and
            want to use a specific one.

        timeout (`int` | `float`, optional):
            The timeout in seconds to be used when connecting.
            This is **not** the timeout to be used when ``await``'ing for
            invoked requests, and you should use ``asyncio.wait`` or
            ``asyncio.wait_for`` for that.

        request_retries (`int` | `None`, optional):
            How many times a request should be retried. Request are retried
            when Telegram is having internal issues (due to either
            ``errors.ServerError`` or ``errors.RpcCallFailError``),
            when there is a ``errors.FloodWaitError`` less than
            `flood_sleep_threshold`, or when there's a migrate error.

            May take a negative or `None` value for infinite retries, but
            this is not recommended, since some requests can always trigger
            a call fail (such as searching for messages).

        connection_retries (`int` | `None`, optional):
            How many times the reconnection should retry, either on the
            initial connection or when Telegram disconnects us. May be
            set to a negative or `None` value for infinite retries, but
            this is not recommended, since the program can get stuck in an
            infinite loop.

        retry_delay (`int` | `float`, optional):
            The delay in seconds to sleep between automatic reconnections.

        auto_reconnect (`bool`, optional):
            Whether reconnection should be retried `connection_retries`
            times automatically if Telegram disconnects us or not.

        sequential_updates (`bool`, optional):
            By default every incoming update will create a new task, so
            you can handle several updates in parallel. Some scripts need
            the order in which updates are processed to be sequential, and
            this setting allows them to do so.

            If set to `True`, incoming updates will be put in a queue
            and processed sequentially. This means your event handlers
            should *not* perform long-running operations since new
            updates are put inside of an unbounded queue.

        flood_sleep_threshold (`int` | `float`, optional):
            The threshold below which the library should automatically
            sleep on flood wait and slow mode wait errors (inclusive). For instance, if a
            ``FloodWaitError`` for 17s occurs and `flood_sleep_threshold`
            is 20s, the library will ``sleep`` automatically. If the error
            was for 21s, it would ``raise FloodWaitError`` instead. Values
            larger than a day (like ``float('inf')``) will be changed to a day.

        raise_last_call_error (`bool`, optional):
            When API calls fail in a way that causes Telethon to retry
            automatically, should the RPC error of the last attempt be raised
            instead of a generic ValueError. This is mostly useful for
            detecting when Telegram has internal issues.

        device_model (`str`, optional):
            "Device model" to be sent when creating the initial connection.
            Defaults to 'PC (n)bit' derived from ``platform.uname().machine``, or its direct value if unknown.

        system_version (`str`, optional):
            "System version" to be sent when creating the initial connection.
            Defaults to ``platform.uname().release`` stripped of everything ahead of -.

        app_version (`str`, optional):
            "App version" to be sent when creating the initial connection.
            Defaults to `telethon.version.__version__`.

        lang_code (`str`, optional):
            "Language code" to be sent when creating the initial connection.
            Defaults to ``'en'``.

        system_lang_code (`str`, optional):
            "System lang code"  to be sent when creating the initial connection.
            Defaults to `lang_code`.

        loop (`asyncio.AbstractEventLoop`, optional):
            Asyncio event loop to use. Defaults to `asyncio.get_event_loop()`.
            This argument is ignored.

        base_logger (`str` | `logging.Logger`, optional):
            Base logger name or instance to use.
            If a `str` is given, it'll be passed to `logging.getLogger()`. If a
            `logging.Logger` is given, it'll be used directly. If something
            else or nothing is given, the default logger will be used.

        receive_updates (`bool`, optional):
            Whether the client will receive updates or not. By default, updates
            will be received from Telegram as they occur.

            Turning this off means that Telegram will not send updates at all
            so event handlers, conversations, and QR login will not work.
            However, certain scripts don't need updates, so this will reduce
            the amount of bandwidth used.
    """
    ```