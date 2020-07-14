import json

from uuid import uuid4
from typing import Optional
from main import Component, fetch


class Root(Component):
    """ This is the root of the application. It is rendered first and
    serves as the starting point for all other components that are visible.
    The template defines what the app will look like.
    """

    tag = "main"
    template = """
        <div class="uk-container">

            <h1 class="uk-margin-medium-bottom">Counter examples</h1>
            <my-counter />

            <hr class="uk-divider-icon" />

            <h1 class="uk-margin-medium-bottom">Todo app example</h1>
            <todo-component />

        </div>
    """


class TodoItem:
    """ Helper class that will structure what a todo item looks like.

    Args:
        title (str): The title of the todo item
        is_done (bool): Whether the todo item is already done
    """
    def __init__(self, title: str, is_done: Optional[bool] = False) -> None:
        self.id = str(uuid4())
        self.title = title
        self.is_done = is_done


class TodoComponent(Component):
    """ The todo component on the page. The todo component will be rendered
    everywhere where the tag "todo-component" is used in a template. The template
    is a Jinja2 template that will render all items in the list.
    """

    tag = "todo-component"
    initial_state = {"todolist": []}
    template = """
        <div class="uk-grid-small" uk-grid>
            <div class="uk-width-3-4@s">
                <input id="todoInput" class="uk-input" type="text" placeholder="Your todo item here" />
            </div>
            <div class="uk-width-1-4@s">
                <button class="uk-button uk-button-primary uk-width-1-1" on:click="new_item">Add</button>
            </div>
        </div>

        <ul class="uk-list uk-list-divider">
            {% for item in todolist %}
                <li>
                    <div class="uk-grid-small" uk-grid>
                        <div class="uk-width-3-4@s">
                            <p style="{{'text-decoration: line-through;' if item.is_done }}">{{ item.title }}</p>
                        </div>
                        <div class="uk-width-1-4@s uk-grid-small" uk-grid>
                            <div class="uk-width-1-2@s">
                                <button class="uk-button uk-width-1-1" on:click="toggle_done" index={{ item.id }}>Done</button>
                            </div>
                            <div class="uk-width-1-2@s">
                                <button class="uk-button uk-button-danger uk-width-1-1" on:click="remove_item" index={{ item.id }}>Remove</button>
                            </div>
                        </div>
                    </div>
                </li>
            {% endfor %}
        </ul>
    """

    def on_mount(self) -> None:
        """ This method runs when the component is first mounted on the page. It
        uses the fetch API to retrieve some todo items from an API. Then, it will
        add the retrieved items to the state of this component so they get rendered.
        """

        def create_initial_todos(data: str) -> None:
            """ Helper method to parse a string as JSON data and convert the data into
            todo items.

            Args:
                data (str): The raw JSON string to parse
            """

            # Parse as JSON (only use the first 2 todo items)
            items = json.loads(data)[:2]

            # Set the state to the newly retrieved items
            self.set_state(
                "todolist",
                [TodoItem(title=item["title"], is_done=True) for item in items],
            )

        # Use the fetch API to retrieve some sample todos
        fetch("https://jsonplaceholder.typicode.com/todos").then(create_initial_todos)

    def new_item(self, event) -> None:
        """ Create a new todo item. This method is called when the add button is clicked.

        Args:
            event (JS click event): The click event from the browser (JsProxy)
        """

        # Get the text from the input field
        title = self.get_element_by_id("todoInput").value

        # If a title was set
        if title != "":

            # Create a new item and add it to the state
            self.state["todolist"] = [TodoItem(title=title), *self.state["todolist"]]

            # Clear the input field to create another todo item
            self.clear_input_field()

    def remove_item(self, event) -> None:
        """ Remove an item from the todo list. This method is called when the remove button
        is clicked.

        Args:
            event (JS click event): The click event from the browser (JsProxy)
        """

        # Set the state to the list of todos, filtered for the one that should be deleted
        self.state["todolist"] = list(
            filter(
                lambda item: item.id != event.target.getAttribute("index"),
                self.state.get("todolist", []),
            )
        )

    def clear_input_field(self) -> None:
        """ Clear the input field of the todo items.
        """

        # Get the input field, set the value to an empty string
        self.get_element_by_id("todoInput").value = ""

    def toggle_done(self, event) -> None:
        """ Set a todo item to done. This will create a strike through effect on
        the item in the list.

        Args:
            event (JS click event): The click event from the browser (JsProxy)
        """

        # Get all the todo items from the state
        state = self.state["todolist"]

        # Loop the todo items, set the selected one to done
        for index, item in enumerate(state):
            if item.id == event.target.getAttribute("index"):
                state[index].is_done = not state[index].is_done

        # Update the state
        self.set_state("todolist", state)


class Counter(Component):
    """ Component that will display a simple counter.
    """

    tag = "my-counter"
    template = """
        <div class="uk-margin-large">
            <p><span>The counter is at </span><span class="counter {{"red" if count < 0 else "green"}}">{{ count }}</span></p>
            <button class="uk-button uk-button-default uk-margin-right" on:click="decrease"> Decrease </button>
            <button class="uk-button uk-button-default" on:click="increase"> Increase </button>
        </div>
    """
    css = """
        .counter {
            font-weight: bold;
        }
        .red {
            color: #f0506e;
        }
        .green {
            color: #32d296;
        }
    """
    initial_state = {"count": 0}

    def increase(self, event) -> None:
        """ Increase the number of the counter.

        Args:
            event (JS click event): The click event from the browser (JsProxy)
        """
        self.state["count"] += 1

    def decrease(self, event) -> None:
        """ Decrease the number of the counter.

        Args:
            event (JS click event): The click event from the browser (JsProxy)
        """
        self.state["count"] -= 1
