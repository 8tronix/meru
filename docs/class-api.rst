Class API
=========

Processses
----------

Processes are modeled as classe that derive from :py:class:`meru.processes.base`:

.. code-block:: python
    :caption: a_process.py

    from meru.processes.base import MeruProcess, action_handler

    class AProcess(MeruProcess):
        # action handlers are decorated methods:

        @action_handler
        def handle_an_action(self, action: AnAction):
            return AnotherAction()

        # no entrypoint definition is needed

Processes need to be registered to be available in the CLI:

.. code-block:: python
    :caption: cli.py

    from meru.actions import discover_actions
    from meru.command_line import main_cli, register_process

    from .processes.a_process import AProcess

    def main():
        # …
        register_process("process1", AProcess())
        # …
        discover_actions("project_root.actions")
        main_cli()

    if __name__ == '__main__':
        main()

For testing purposes, the methods can be called as regular methods:

.. code-block:: python
    :caption: a_test.py

    from a_process import AProcess

    process = AProcess()
    process.initialize()
    # instead of calling process.run(), we interact with the handlers directly
    responses = list(process.handle_an_action(AnAction(question="What is 6•9?")))
    assert responses == [AnotherAction(answer="42")]
