### Front-end URL structure

```
https://<domain-name>[/<base-path>]/<app-name>/<page-name>[</arg_1:value>][/<arg_2:value>]?[sid=ZqTSAsfJz96rPaJYDbVLxZ][&param1=def][&param2=tuv]
```

### Page State

Page State is managed by

```javascript
PageState = {
    "name": "<page-name>",
    "time": "<page-state creation time>",
    "args": [ // Page arguments
        ["arg_1", "value"],
        ["arg_2", "value"]
    ],
    "link_state": {  // Url params
        "param1": "def",
        "param2": "tuv"
    },
    "vars_state": {
        // Variables internal state, saved in link / local storage if too big
        // The share internal state may optionally peristed on server using the state _id
        // Upon the page is loaded, a new state _id must be generated
        "_id": "ZqTSAsfJz96rPaJYDbVLxZ"  // shortuuid
        "custom": "value"
    },
    "priv_state": { // Private state is not persisted, across link, it is only stored with in localstorage.
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

Each component has a schema to validate its initialization parameters, which is a combination of page.args & states.

Page Component state schema should be declare it state structure (e.g) as a schema list:

[
    LinkState('link_state_name', READONLY | WRITABLE, [alias]),
    VarsState('vars_state_name', READONLY | WRITABLE, [alias]),
    PrivState('priv_name', [alias]) // Private state are always writable
]

Only one component can register writable state (determined by alias). Link & Vars

```typescript

enum ComponentStateType {
  LINK = "LINK",
  VARS = "VARIATE",
  PRIV = "PRIVATE"
}

// Base class
class ComponentState {
  protected name: string;
  protected value: any;
  protected type: ComponentStateType;
  protected permission

  constructor(name: string) {
    this.name = name;
    this.value = null; // default value
  }

  getValue(): any {
    return this.value;
  }

  setValue(newValue: any): void {
    this.value = newValue;
  }
}

// Derived class: LinkComponentState
class LinkComponentState extends ComponentState {
  protected type: ComponentStateType = ComponentStateType.LINK;
  constructor(name: string) {
    super(name);
  }

  // Additional logic specific to LinkComponentState can go here
}

// Derived class: SharedComponentState
class VariablesComponentState extends ComponentState {
  protected type: ComponentStateType = ComponentStateType.VARS;
  constructor(name: string) {
    super(name);
  }

  // Additional logic specific to SharedComponentState can go here
}

// Derived class: PrivateComponentState
class PrivateComponentState extends ComponentState {
  protected type: ComponentStateType = ComponentStateType.PRIV;
  constructor(name: string) {
    super(name);
  }

  // Additional logic specific to PrivateComponentState can go here
}
```

Each component has access to the page state and can write values to the shared page state.

To prevent multiple components from writing conflicting values to the page state, the components must register their state attribute names.

Each unique component may register it run-time state in the private state.


### Page link generation

Whenever a page link is requested, if there is data in the share state:
- A new state ID is generated
- Current state is saved into the state ID
- State ID, args, params, page-name are incorporated into the URL
