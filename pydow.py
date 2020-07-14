from __future__ import annotations

import re
import sys
import uuid
import types

from collections.abc import MutableMapping
from js import document, window, Node  # type: ignore
from bs4 import BeautifulSoup
from bs4.element import Tag
from typing import Type, Any, Dict, Callable, Optional, TypeVar, Union
from jinja2 import Template


# Create a custom type for type hinting
JsProxy = TypeVar("JsProxy")
Promise = TypeVar("Promise")

DEBUG = False


class GroupedLogs:
    def __init__(self, groupName: str, closed: bool = False) -> None:
        self.groupName = groupName
        self.closed = closed

    def __enter__(self) -> None:
        if DEBUG:
            if self.closed:
                console.groupCollapsed(self.groupName)
            else:
                console.group(self.groupName)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if DEBUG:
            console.groupEnd()


# Add shortcut
console = window.console
console.grouped = GroupedLogs


class fetch:
    """ Wrap the fetch API of the browser.
    """

    def __call__(self, url: str, options: Dict[str, Any] = {}) -> Promise:
        return window.fetch(url).then(lambda response: response.text())


class DictDiffer:
    """ Calculate the difference between 2 dictionaries.
    """

    def __init__(self, current_dict: Dict[str, Any], past_dict: Dict[str, Any]) -> None:
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = (
            set(current_dict.keys()),
            set(past_dict.keys()),
        )
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(
            o for o in self.intersect if self.past_dict[o] != self.current_dict[o]
        )


class State(MutableMapping):
    """A dictionary that applies an arbitrary key-altering
       function before accessing the keys"""

    def __init__(self, dom: Dom, *args, **kwargs):
        self.initialized = False
        self.dom = dom
        self.store = dict()
        self.update(dict(*args, **kwargs))
        self.initialized = True

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value
        if self.initialized:
            self.dom.render()

    def __delitem__(self, key):
        del self.store[key]
        if self.initialized:
            self.dom.render()

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)


class Component:

    tag = ""
    template = ""
    css = ""

    def __init__(
        self,
        dom,
        tag: Optional[str] = None,
        content: Optional[str] = None,
        event_handlers: Dict[str, Callable] = {},
        attributes: Dict[str, Any] = {},
        template: Optional[str] = None,
        top_custom_component: Optional[Component] = None,
    ) -> None:

        # Create a new unique identifier for this component
        self.identifier = str(uuid.uuid4())

        # Store a reference to the DOM
        self.dom = dom

        # Initialize other attributes (empty by default)
        self.element = None
        self.children = []
        self.content = content
        self.event_handlers = event_handlers
        self.attributes = attributes

        # Create a store for maintaining the state of this component
        self._state = State(dom=self.dom, **getattr(self, "initial_state", {}))

        # Get a reference to the closesed custom defined component
        if top_custom_component is None:
            self.top_custom_component = self
        else:
            self.top_custom_component = top_custom_component

        # Set the template of this component
        if not hasattr(self, "template") or getattr(self, "template") == "":
            if template is not None:
                self.template = template
            else:
                self.template = ""
        self._template = Template(self.template)

        # Set the (HTML)tag of this component
        if tag is not None:
            self.tag = tag

    def get_element_by_id(self, identifier: str) -> JsProxy:
        return document.querySelector(
            f'{self.tag}[identifier="{self.identifier}"] #{identifier}'
        )

    def query_selector(self, query: str):
        return document.querySelector(
            f'{self.tag}[identifier="{self.identifier}"] {query}'
        )

    def on_mount(self):
        pass

    @property
    def state(self) -> Any:
        return self._state

    @state.setter
    def state(self, newValue: Dict[str, Any]) -> None:
        self._state = newValue

    def get_state(self, key: str, default: Optional[Any] = None) -> Any:
        return self._state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        self._state[key] = value

    def set_global_state(self, key: str, value: Any) -> None:
        self.dom.state[key] = value

    def get_global_state(self, key: str, default: Optional[Any] = None) -> Any:
        return self.dom.state.get(key, default)

    def render_template(self) -> str:
        state = {
            **self.dom.state,
            **dict(self.top_custom_component._state),
        }
        return self._template.render(**state)

    def _set_attribute(self, attribute: str, value: Union[str, list]):
        if isinstance(value, list):
            self.element.setAttribute(attribute, " ".join(value))
        else:
            self.element.setAttribute(attribute, value)

    def _create_element(self, parent_element: JsProxy) -> JsProxy:

        # Create a DOM element to represent this object
        self.element = document.createElement(self.tag)
        if self.top_custom_component == self:
            self.element.setAttribute("identifier", self.identifier)

        # Set attributes
        for attribute, value in self.attributes.items():
            self._set_attribute(attribute, value)

        # Add the element to its parent
        if parent_element is not None:
            parent_element.appendChild(self.element)

        # Create event listeners
        for event, handler in self.event_handlers.items():
            self.element.addEventListener(event, handler)

        # Add any content (text)
        if self.content is not None:
            self.element.appendChild(document.createTextNode(self.content))

        # Run the onMount function of the component
        self.on_mount()

    def _update_event_handlers(self, oldEvent_handlers: Dict[str, Callable]) -> None:

        # Check which event handlers have changed, and update accordingly
        diff = DictDiffer(self.event_handlers, oldEvent_handlers)
        for key in diff.added():
            self.element.addEventListener(key, self.event_handlers[key])
        for key in diff.changed():
            self.element.removeEventListener(key, oldEvent_handlers[key])
            self.element.addEventListener(key, self.event_handlers[key])
        for key in diff.removed():
            self.element.removeEventListener(key, oldEvent_handlers[key])
        self.event_handlers = {**oldEvent_handlers, **self.event_handlers}

    def _update_attributes(self, oldAttributes: Dict[str, Any]) -> None:

        # Check which attributes have changed, and update accordingly
        diff = DictDiffer(self.attributes, oldAttributes)
        for key in diff.added():
            self._set_attribute(key, self.attributes[key])
        for key in diff.changed():
            self._set_attribute(key, self.attributes[key])
        for key in diff.removed():
            self.element.removeAttribute(key)
        self.attributes = {**oldAttributes, **self.attributes}

    def _update_content(self):

        # Get the desired content of this element (should always be a string)
        content = "" if self.content is None else self.content

        # Get the current content from the element, use a special filter to only get text of this element, not the children
        current_content = "".join(
            (
                list(
                    map(
                        lambda element: element.textContent,
                        filter(
                            lambda element: element.nodeType == Node.TEXT_NODE,
                            self.element.childNodes,
                        ),
                    )
                )
            )
        )

        # If the content changed, update the element
        if current_content != content:
            self.element.textContent = self.content

    def _create_children(self):

        # Parse the template of the component to create nested components
        sub_template = BeautifulSoup(self.render_template())
        children = sub_template.find_all(recursive=False)
        new_children = []
        if len(children) > 0:

            # Loop the children from the template
            for i in range(len(children)):
                child = children[i]

                if isinstance(child, Tag):

                    # Get the attributes
                    attrs = dict(
                        {
                            key: value
                            for key, value in getattr(child, "attrs", {}).items()
                            if not key.startswith("on:")
                        }
                    )

                    # Extract event handlers
                    event_handlers = {
                        key[3:]: getattr(
                            self.top_custom_component,
                            value,
                            lambda x: print("not implemented"),
                        )
                        for key, value in dict(getattr(child, "attrs", {})).items()
                        if key.startswith("on:")
                    }

                    # Create a custom or default component
                    if child.name in self.dom.components:
                        new_component = self.dom.components[child.name](
                            dom=self.dom,
                            content=child.string,
                            event_handlers=event_handlers,
                            attributes=attrs,
                            template=" ".join(
                                [str(x) for x in child.find_all(recursive=False)]
                            ),
                        )
                    else:
                        new_component = Component(
                            tag=child.name,
                            dom=self.dom,
                            content=child.string,
                            event_handlers=event_handlers,
                            attributes=attrs,
                            template=" ".join(
                                [str(x) for x in child.find_all(recursive=False)]
                            ),
                            top_custom_component=self.top_custom_component,
                        )

                    # Determine if there was already an item there
                    if len(self.children) > i:
                        previous = self.children[i]
                    else:
                        previous = None

                    # Render the new component as a child of this component (recursion)
                    new_component.render(
                        parent_element=self.element, previous_tree=previous
                    )

                    # Add it to the list for future reference
                    new_children.append(new_component)

                else:
                    raise Exception("child is not a Tag")

            # Remove any children that aren't supposed to be there anymore
            for child in self.children[len(children) :]:
                child.element.remove()

            # Set the children of this component, to the just created children
            self.children = new_children

        # No children from the sub_template, remove any pre-existing children
        else:
            self.children = []
            while self.element.lastElementChild is not None:
                self.element.removeChild(self.element.lastElementChild)

        return new_children

    def render(
        self, parent_element: JsProxy, previous_tree: Optional[Component] = None
    ) -> Component:

        # If there was no previous item, create it
        if previous_tree is None:
            self._create_element(parent_element=parent_element)

        elif (
            type(self) == type(previous_tree)
            and self.__class__.__name__ == previous_tree.__class__.__name__
        ):

            # Copy the info from the previous element, since they are the same
            self.identifier = previous_tree.identifier
            self.children = previous_tree.children
            self.element = previous_tree.element
            self._state = previous_tree._state

            # Update event handlers
            self._update_event_handlers(oldEvent_handlers=previous_tree.event_handlers)

            # Update attributes
            self._update_attributes(oldAttributes=previous_tree.attributes)

            # Update the content (text)
            self._update_content()

        self.children = self._create_children()
        return self


class Dom:
    def __init__(self, root: Type[Component], selector: str) -> None:

        # Gather all components that are defined in the global space
        self.components = {
            component.tag: component
            for component in list(
                [
                    value
                    for value in globals().values()
                    if isinstance(value, type)
                    and issubclass(value, Component)
                    and value.__name__ != "Component"
                ]
            )
        }

        # Gather all the CSS
        self.css = []
        for component in self.components.values():
            if component.css != "":

                # Scope the CSS by prefixing it with the component tag
                css = re.sub(
                    r"([^\r\n,{}\s]+)(,(?=[^}]*{)|\s*{)",
                    f"{component.tag} \\1 {{",
                    component.css,
                )
                lines = list([line for line in css.split("\n") if line.rstrip() != ""])
                self.css.append("\n".join(lines))

        # Add the CSS to the head of the document
        styleElement = document.createElement("style")
        styleElement.type = "text/css"
        styleElement.innerHTML = "\n".join(self.css)
        document.head.appendChild(styleElement)

        # Create the root component
        self.root = root(dom=self)
        self.previous_tree = None
        self.state = State(dom=self)

        # Find the root element in the document
        self.element = document.querySelector(selector)

        # Render the DOM, starting from the root component
        self.render()

    def render(self) -> None:

        # Render the root component
        self.previous_tree = self.root.render(
            parent_element=self.element, previous_tree=self.previous_tree
        )


# Create a module from the code above
main = types.ModuleType("main")

# Add the elements to the module
main.Component = Component
main.Dom = Dom
main.fetch = fetch()
main.console = console

# Add the module to the sytem
sys.modules["main"] = main
