import json
import os
import paramiko
import pipes
import pwd
import re
import requests
from urllib.parse import urlencode


class BaseConnection(object):
    """Query a PuppetDB instance supporting the v4 API."""

    def connect(self):
        pass

    def disconnect(self):
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def query(self, query, order_by=None, limit=None, timeout=60):
        params = {'query': query}
        if order_by is not None and len(order_by):
            if isinstance(order_by, (str, tuple)):
                order_by = [order_by]

            params['order_by'] = []
            for sort in order_by:
                if isinstance(sort, str):
                    params['order_by'].append({'field': sort, 'order': 'asc'})
                else:
                    params['order_by'].append({'field': sort[0], 'order': sort[1]})
            params['order_by'] = json.dumps(params['order_by'])

        if limit is not None:
            params['limit'] = str(limit)

        try:
            return self._request_json(
                "query/v4?" + urlencode(params),
                timeout=timeout)
        except ResponseError as e:
            raise QueryError(e.message, query) from None

    def _request_json(self, uri, timeout):
        raise NotImplementedError()


class HTTPConnection(BaseConnection):
    def __init__(self):
        self.url = "http://localhost:8080/pdb"

    def _request_json(self, uri, timeout):
        response = requests.get(
            "{0}/{1}".format(self.url, uri),
            timeout=timeout)

        ### FIXME: make error the same as SSH
        response.raise_for_status()
        return response.json()


class SSHConnection(BaseConnection):
    def __init__(self, server, username=None, password=None, ignore_host_keys=True):
        self.server = server
        self.username = username
        self.password = password
        self.ignore_host_keys = ignore_host_keys
        self._client = None

    # Update server and username based on ~/.ssh/config and the OS user.
    def load_ssh_config(self):
        path = os.path.expanduser("~/.ssh/config")
        if not os.path.isfile(path):
            return

        config = paramiko.SSHConfig()
        config.parse(open(path))
        host = config.lookup(self.server)

        self.server = host["hostname"]
        if self.username is None:
            if "user" in host:
                self.username = host["user"]
            else:
                # Use local username
                self.username = pwd.getpwuid(os.getuid()).pw_name

    def connect(self):
        # Be sure that the connection isn't open.
        self.disconnect()

        self.load_ssh_config()

        self._client = paramiko.SSHClient()
        self._client.load_system_host_keys()
        if self.ignore_host_keys:
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(hostname=self.server, username=self.username, password=self.password)

    def disconnect(self):
        if self._client:
            self._client.close()
            self._client = None

    def _request_json(self, uri, timeout):
        url = "http://localhost:8080/pdb/{0}".format(uri)

        stdin, stdout, stderr = self._client.exec_command(
            command="curl -sXGET {0}".format(pipes.quote(url)),
            timeout=timeout)

        response = stdout.read()
        try:
            return json.loads(response)
        except json.decoder.JSONDecodeError:
            raise ResponseError(response.decode("utf-8", "strict"), url) from None

def AutomaticConnection(server):
    if server == "localhost":
        return HTTPConnection()
    else:
        return SSHConnection(server)

class ResponseError(Exception):
    """Error returned by PuppetDB API."""
    def __init__(self, message, url):
        super(ResponseError, self).__init__(message)
        self.url = url
        self.message = message

    def __str__(self):
        s = super(ResponseError, self).__str__()
        return "{0}\n    URL: {1}".format(s, self.url)

class QueryError(Exception):
    """Error returned by PuppetDB query endpoint."""
    def __init__(self, message, query):
        super(QueryError, self).__init__(message)
        self.query = query
        self.message = message

    def __str__(self):
        s = super(QueryError, self).__str__()
        return "{0}\n    Query: {1}".format(s, self.query)

class QueryFilter(object):
    def __init__(self, filters=set()):
        self.filters = set(filters)

    def add(self, filter):
        self.filters.add(filter)

    def __call__(self, query, *args):
        """Take the query apart and add self.filters to it"""
        match = re.search(r'\A(\s*\w+\s*(?:\[[^{]*\])?\s*\{\s*)(.*?)(\s*\})\s*\Z', query)
        if not match:
            raise ValueError("Invalid query: {0}".format(query))

        filters = filter(None, [match.group(2)] + sorted(self.filters.union(args)))
        filters = " and ".join(["(%s)" % f for f in filters])

        return "".join([match.group(1), filters, match.group(3)])
