# Service Shutdown & Thread Lifecycle

How `service.py` shuts down, and the rules Kodi enforces. Written after
diagnosing a recurring `script didn't stop in 5 seconds - let's kill it`
force-kill on quit (verified empirically against `~/Library/Logs/kodi.log`).

## How shutdown is triggered

`service.py` is a long-running `xbmc.service` (`start="login"`) with a 1-second
poll loop. It exits two ways, **both intentionally kept**:

1. **`System.OnQuit`** notification → `PlaybackService.onNotification`
   (`resources/lib/play_utils.py`) sets the HomeWindow `exit` property to
   `'True'` → the loop condition sees it.
2. **Abort signal** → the loop checks `abort_monitor.abortRequested()` and ticks
   with `abort_monitor.waitForAbort(1)` (the canonical Kodi pattern; see
   [Monitor docs](https://xbmc.github.io/docs.kodi.tv/master/kodi-dev-kit/group__python__monitor.html)).

`abort_monitor` is a dedicated `xbmc.Monitor()` kept **separate** from
`monitor = Service()` (an `xbmc.Player`) that reuses the name later in the file —
don't collapse them or abort detection dies.

## The 5-second force-kill rule (the important part)

On quit, Kodi's `CPythonInvoker` waits up to **5 seconds** for **every thread the
service spawned**, then force-kills. Non-obvious facts, all verified:

- **`daemon=True` does NOT exempt a thread from Kodi's wait.** A daemon
  `WebSocketClient` was still waited on and still triggered the kill. The *only*
  fix is making each helper thread genuinely terminate within 5s. Don't reach for
  the daemon flag — it does nothing here.
- **`waitForAbort(n)` returns immediately once abort is requested.** So it's
  useless as a post-shutdown "grace" delay; for diagnostics use a real
  `time.sleep`.
- Diagnose lingering threads by logging `threading.enumerate()` with
  `t.__class__.__name__` (thread names are just `Thread-N`).

### Threads spawned by the service & how they exit

| Thread | Exits via | Notes |
| --- | --- | --- |
| `WebSocketClient` | `run_forever()` returns on `close()` | **Was the blocker.** See below. |
| `HttpImageServerThread` | `stop()` → `shutdown()` + `server_close()` | Must close the socket or the port stays bound. |
| `LibraryChangeMonitor` | `waitForAbort(10)` (wakes on abort) | exits ~instantly on abort |
| `ContextMonitor` | `xbmc.sleep(≤1000)` loop + `abortRequested()` | exits ≤1s |
| `IntroSkipperService` | `waitForAbort(1)` | exits ≤1s |

## Two real bugs fixed (don't reintroduce)

### 1. WebSocket `run_forever(reconnect=...)` never returns

`WebSocketClient.run()` used `self._client.run_forever(reconnect=30)`. The
`reconnect=` argument keeps `run_forever` in an **internal auto-reconnect loop
that `close()` cannot reliably break**, so the thread outlived the 5s budget →
force-kill. Fix: call `run_forever()` **without** `reconnect=`; the outer
`while` loop already reconnects, and it's abort-aware via `waitForAbort(20)`.

Also: `stop_client()` cancels the pending keepalive `threading.Timer(30, …)`
(tracked as `self._keepalive_timer`) — otherwise that 30s timer thread keeps the
process alive past the budget. And `on_open` uses `waitForAbort(30)` instead of
`time.sleep(30)`.

### 2. Image server leaves its port bound

`HttpImageServerThread.stop()` called only `self.server.shutdown()`. That stops
`serve_forever()` but does **not** release the listening socket. After a
force-kill the port stayed bound, so the next launch's
`HTTPServer(('', PORT_NUMBER), …)` failed with *Address already in use* →
`run()` threw before assigning `self.server` → the *next* `stop()` raised
`'HttpImageServerThread' object has no attribute 'server'`. Fix: `stop()` guards
`self.server` and calls both `shutdown()` **and** `server_close()`; `run()`
wraps the bind in try/except and `__init__` sets `self.server = None`.

## Verified result

Original code: `script didn't stop in 5 seconds - let's kill it` on quit.
After the fixes: both threads join in ~0.9s, the next add-on proceeds, no kill.

## Logging gotcha (for any future diagnosis here)

Add-on logs always emit to `kodi.log` at `xbmc.LOGINFO`, but
`resources/lib/loghandler.py:_get_log_level` filters by the add-on's own
**`log_debug`** setting — *not* Kodi's `debug.showloginfo`. With
`log_debug=false`, `log.debug(...)` lines are dropped; `log.info`/`log.error`
always appear. So for temporary shutdown instrumentation, log at `info`.
Kodi log path (macOS): `~/Library/Logs/kodi.log` (truncated on each Kodi start).
