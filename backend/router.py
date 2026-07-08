"""Minimal REST router: method + path matching with `:param` support,
JSON I/O, and role-based access control.
"""
import re

import auth
import db


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class Context:
    """Everything a handler needs about the current request."""

    def __init__(self, method, params, query, body, user):
        self.method = method
        self.params = params      # path params, e.g. {"id": "3"}
        self.query = query        # query string params, dict of str->str
        self.body = body or {}    # parsed JSON body
        self.user = user          # current user row dict, or None

    def param_int(self, name):
        try:
            return int(self.params[name])
        except (KeyError, ValueError):
            raise ApiError(400, f"Invalid path parameter: {name}")

    def require(self, *fields):
        missing = [f for f in fields if self.body.get(f) in (None, "")]
        if missing:
            raise ApiError(400, "Missing required fields: " + ", ".join(missing))


class Router:
    def __init__(self):
        self._routes = []  # list of (method, regex, param_names, handler, roles)

    def add(self, method, pattern, handler, roles=None):
        param_names = re.findall(r":(\w+)", pattern)
        regex = "^" + re.sub(r":(\w+)", r"(?P<\1>[^/]+)", pattern) + "$"
        self._routes.append((method.upper(), re.compile(regex), param_names, handler, roles))

    def route(self, method, roles=None):
        def deco(fn):
            # pattern is read from the function's `path` attribute set below
            self.add(method, fn.path, fn, roles)
            return fn
        return deco

    def _current_user(self, headers):
        authz = headers.get("Authorization", "")
        if not authz.startswith("Bearer "):
            return None
        payload = auth.decode_token(authz[7:])
        if not payload:
            return None
        return db.query_one("SELECT * FROM users WHERE id = ?", (payload["sub"],))

    def dispatch(self, method, path, query, body, headers):
        """Return (status, body_dict)."""
        user = self._current_user(headers)
        matched_path = False
        for m, regex, _names, handler, roles in self._routes:
            match = regex.match(path)
            if not match:
                continue
            matched_path = True
            if m != method:
                continue
            # RBAC
            if roles is not None:
                if user is None:
                    return 401, {"error": "Authentication required"}
                if user["role"] not in roles:
                    return 403, {"error": "Insufficient permissions"}
            ctx = Context(method, match.groupdict(), query, body, user)
            try:
                return handler(ctx)
            except ApiError as e:
                return e.status, {"error": e.message}
            except Exception as e:  # noqa: BLE001
                return 500, {"error": "Internal error: " + str(e)}
        if matched_path:
            return 405, {"error": "Method not allowed"}
        return 404, {"error": "Not found"}
