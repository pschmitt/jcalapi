# 📅 jcalapi

jcalapi is a local calendar cache and JSON API that interacts with Exchange and 
Confluence calendars. It fetches events and returns them in a JSON format, 
making it easy to integrate calendar data into other systems.

## 🚀 Getting Started

### 📋 Prerequisites

- Python
- [Poetry](https://python-poetry.org)

### 🔑 Setting Up Credentials

To use jcalapi, you'll need to provide credentials for accessing your Exchange 
or Confluence calendars. These credentials should be stored in a secure 
location, and you should ensure that they are not exposed in your code or 
version control system.

For Exchange, you'll need your username and password. 
For Confluence, you'll need your API token.

See [.envrc.sample](./envrc.sample) for an example.

### 💾 Installation

1. Clone the repository
```shell
git clone https://github.com/pschmitt/jcalapi.git
```

2. Navigate into the cloned repository
```shell
cd jcalapi
```

3. Setup the environment
```shell
poetry install
```

### 🏃 Usage

You can run the application directly using Python:

```shell
python main.py
```

## 📚 API Usage

The API provides endpoints for fetching calendar events. Here's an example of how to use it:

```shell
curl http://localhost:7042/today
```

This will return a JSON response with the events data:

```json
[
  {
    "uid": "event1",
    "backend": "exchange",
    "calendar": "calendar1",
    "organizer": "organizer1",
    "summary": "event1 summary",
    "description": "event1 description",
    "body": "event1 body",
    "location": "event1 location",
    "start": "2023-06-06T00:00:00",
    "end": "2023-06-06T01:00:00",
    "whole_day": false,
    "status": "confirmed",
    "extra": {
      "conference_type": "Teams",
      "meeting_workspace_url": "https://teams.microsoft.com/l/meetup-join/...",
      "net_show_url": "https://teams.microsoft.com/l/meetup-join/..."
    },
    "conference_url": "https://teams.microsoft.com/l/meetup-join/..."
  },
  ...
]
```

To fetch events for tomorrow, you can use the `/tomorrow` endpoint:

```shell
curl http://localhost:7042/tomorrow
```

This will return a JSON response with the events data for tomorrow.

The `/meta` endpoint provides metadata about the backends (Confluence/Exchange):

```shell
curl http://localhost:7042/meta
```

The `/reload` endpoint allows you to reload the calendar data:

```shell
curl -X POST http://localhost:7042/reload
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a pull request.

## 📄 License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
