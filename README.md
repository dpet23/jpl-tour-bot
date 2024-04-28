Scrape the NASA JPL tours and notify if a reservation can be made.

> https://www.jpl.nasa.gov/events/tours/


## Requirements

* [Python 3.10](https://www.python.org/downloads/) or newer,
  and Pip
* [Chrome 109](https://www.google.com/chrome/) or newer,
  and [ChromeDriver](https://googlechromelabs.github.io/chrome-for-testing/)


## Usage

1. Install the [Google Chrome](https://www.google.com/chrome/) browser, if it's not already installed.

2. Download the [chromedriver](https://googlechromelabs.github.io/chrome-for-testing/#stable) for your platform
   and unzip the downloaded file.
   This allows the bot to interact with the Chrome browser.

3. Install [Python](https://www.python.org/downloads/), to be able to run the bot.

4. Create a new Python virtual environment. From the command-line, run:
   ```
   python -m venv $HOME/.virtualenvs/jpl_tour_bot
   ```

5. Activate the virtual environment:
    * On macOS or Linux, run: `source $HOME/.virtualenvs/jpl_tour_bot/bin/activate`
    * On Windows, use PowerShell to run: `& "$HOME\.virtualenvs\jpl_tour_bot\Scripts\Activate.ps1"`

3. Install the bot and its dependencies:
   ```
   pip install jpl_tour_bot-X.Y.Z-py3-none-any.whl
   ```

4. Run the bot:
   ```
   jpl_tour_bot --browser-binary /path/to/chromedriver
   ```

### Additional features

#### Show the browser UI

By default, the Chrome window is not shown when running the bot.

To show the browser window while the bot is running, add the `--ui` flag:
```
jpl_tour_bot -b /path/to/chromedriver --ui
```

#### Send Discord notifications

The bot can post a message to a Discord channel, notifying of any important changes, like new available tours.

First create a webhook for the Discord channel that should receive the notifications.
See [Discord's instructions](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).

Then use the `--notify` setting to tell the bot to use this webhook:
```
jpl_tour_bot -b /path/to/chromedriver --notify https://discord.com/api/webhooks/...
```

#### Press the "Reserve Now" button

Since tour availability often changes quickly, the bot can press the "Reserve Now" button
for the first available tour within a certain date range.

Use the `--reserve-date-range` setting, along with the first and last dates to search for:
```
jpl_tour_bot -b /path/to/chromedriver --reserve-date-range 2024-07-08 2024-07-12
```

The dates must be specified in [ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html) format
(`YYYY-MM-DD`, year-month-day).

ℹ️ **It's still up to you to fill in the reservation form on the JPL website**,
so the Chrome window will always be shown when this setting is enabled.

#### Increase the page timeout

The bot will wait for 1 minute for a webpage to load, and will fail to run if a page doesn't load in that time.

Use the `--page-timeout` setting to change the timeout value.
For example, this will tell the bot to wait only 15 seconds for a webpage to load:
```
jpl_tour_bot -b /path/to/chromedriver --page-timeout 15
```

### Run the bot on a schedule

The bot will only check the JPL tour availability once and exit.
To automatically run the bot more than once, use your operating system's job scheduler.

When setting up a schedule, be careful of time zones. NASA JPL is in Los Angeles,
convert to the correct time zone using [World Time Buddy](https://www.worldtimebuddy.com/?pl=1&lid=5368361,100&h=5368361&hf=0).

##### Linux

Use the `cron` command-line utility:

1. Open the cron table configuration:
    ```
    crontab -e
    ```

2. Create a scheduled task. Examples:
    * Run the bot every 2 hours, waiting a random amount between 5-45 minutes, and notifying of any tour changes:
      ```
      # minute | hour | day | month | weekday | command
        0        */2    *     *       *         $HOME/.virtualenvs/jpl_tour_bot/bin/jpl_tour_bot -b /path/to/chromedriver -w 300 2700 -n https://discord.com/api/webhooks/...
      ```
    * Run the bot every minute from 9:00am to 11:00am (120 runs) on 6 May, and open the reservation page for a tour:
      ```
      # minute | hour | day | month | weekday | command
        *        9-11   6     5       *         $HOME/.virtualenvs/jpl_tour_bot/bin/jpl_tour_bot -b /path/to/chromedriver -t 15 -r 2024-07-08 2024-07-12 -n https://discord.com/api/webhooks/...
      ```
      Note that environment variables like `$HOME` may not work in cron, and may have to be manually expanded.

3. Save and quit the cron table configuration file.

The bot's logging can be viewed by:
  * Writing it to the syslog:
    ```
    jpl_tour_bot -b /path/to/chromedriver 2>&1 | /usr/bin/logger -t <TAG>
    tail -f /var/log/syslog | grep <TAG>
    ```
  * Writing it to a file:
    ```
    jpl_tour_bot -b /path/to/chromedriver >/path/to/jpl_tour.log 2>&1
    tail -f /path/to/jpl_tour.log
    ```

##### macOS

`launchd` is the preferred way of scheduling tasks.
See the [Apple documentation](https://support.apple.com/en-au/guide/terminal/apdc6c1077b-5d5d-4d35-9c19-60f2397b2369/mac)
or [this tutorial](https://launchd.info/)
for setting it up.

`cron` should still work on macOS, but it is deprecated.
Since macOS Catalina (version 10.15), the `/usr/sbin/cron` executable needs to be added to
System Settings → Privacy & Security → Full Disk Access.

##### Windows

Use the Task Scheduler:

  1. Open the Task Scheduler (`taskschd.msc`)
  2. Right-click on "Task Scheduler Library" and select "Create Task..."
  3. Fill in the form:
     * General → Name: "JPL Tour Bot"
     * Triggers → New... → set your schedule (for example: run one time, repeat every 5 minutes, indefinitely)
     * Actions → New... → fill in the command
  4. OK

Alternatively, the [Windows Subsystem for Linux](https://learn.microsoft.com/en-us/windows/wsl/install) (WSL)
could be used to set up a Linux `cron` job.


## Development

### Virtual Environment Setup

Dependencies are handled by [Poetry](https://python-poetry.org/), and configured in `pyproject.toml`.

Common Bash commands:

* Install Poetry
  * `pip install poetry`

* Configure Poetry to place the virtualenv folder in the project folder
  (created in a `.venv` folder)
  * `poetry config virtualenvs.in-project true`

* Create a new virtualenv
  * `poetry env use python3.10`

* Use the virtuelenv in the same shell
  * `source $(poetry env info --path)/bin/activate`
  * `deactivate`

* Install dependencies
  (the current project is installed in editable mode by default)
  * `poetry install`

* Add a new dependency
  * `poetry add <package> [--group dev]`

* Remove an existing dependency
  * `poetry remove <package> [--group dev]`

* Update installed packages (and lockfile)
  * `poetry update`

### Code Formatting

Code formatting is handled by [Black](https://black.readthedocs.io/en/stable/).

To auto-format, run:
```bash
black [--check --diff] [--config pyproject.toml] .
```

### Code Linting

Due to the lack of automated testing, the codebase heavily relies on static code checking.
Type hints are used to help the code checkers and IDEs.

General code verification is handled by [Ruff](https://docs.astral.sh/ruff/)
and strict type checking is handled by [mypy](https://mypy.readthedocs.io/en/stable/).

To check the code, run:
```bash
ruff check [--no-cache] [--config pyproject.toml] . && mypy .
```

Some issues can be automatically fixed using the `--fix` flag.


## Deployment

### Version Bumping

Use Poetry's commands to change the package version number (in `pyproject.toml`):

```bash
poetry version [major|minor|patch|<string>]
```

### Packaging

To build a release wheel, run:
```bash
poetry build --format wheel
```
