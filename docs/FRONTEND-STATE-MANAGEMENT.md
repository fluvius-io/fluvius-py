### Front-end URL structure

```
https://<domain-name>[/<base-path>]/<app-name>/<page-name>[</arg_1:value>][/<arg_2:value>]?[sid=ZqTSAsfJz96rPaJYDbVLxZ][&abc=def][&ghi=tuv]
```

### PageState

```javascript
PageState = {
    "name": "<page-name>",
    "time": "<page-state creation time>",
    "args": { // Page arguments
        "arg_1": "value"
        "arg_2": "value"
    },
    "params": {  // Url params
        "abc": "def",
        "ghi": "tuv"
    },
    "states": {
        // Share internal state, saved in local storage
        // The share internal state may optionally peristed on server using the state _id
        // Upon the page is loaded, a new state _id must be generated
        "_id": "ZqTSAsfJz96rPaJYDbVLxZ"
        "custom": "value"
    },
    "private": { // Private state is not persisted, it reset whenever the page refresh
        "31003F8B-1DBD-4A2A-A2FE-7AD3DFDA066C": {
            "component": "data"
        }
    },
    "auth": {
        "user": {},
        "profile": {},
        "organization": {}
    },
    "other": {

    }
}
```

### PageManager Specifications

Upon page initialization, the page manager construct the page state by parsing the URL and fetch the initial state using `sid`

Using the page args, it may turn on/off page components as needed.

For each page component, validate the parameters according to the page component schema (combining `page.args` & `page.params`)


### PageComponent Specifications

Page component is the top level components for a page, usually serving as a panel or a common utility (e.g. notifications)

Each component must have an static identifier (i.e. key - alpha_numberic123_underscore), and a unique runtime identifier (i.e. uuid)

Each component has a schema to validate its initialization parameters,
which is a combination of page.args & page.params (which values in page.args take preference)

Each component has access to the page state and can write values to the shared page state.

To prevent multiple components from writing conflicting values to the page state, the components must register their state attribute names.

Each unique component may register it run-time state in the private state.


### Page link generation

Whenever a page link is requested, if there is data in the share state:
- A new state ID is generated
- Current state is saved into the state ID
- State ID, args, params, page-name are incorporated into the URL
