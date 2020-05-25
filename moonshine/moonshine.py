import logging

logger = logging.getLogger(__name__)
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from alembic.config import Config
from alembic import util, autogenerate
from sqlalchemy import engine_from_config, create_engine, MetaData
from sqlalchemy.engine import Engine
import os, sys, io
from contextlib import contextmanager


class Moonshine:

    """
    Only upgrade, downgrade and stamp use env.py
    Offline removed to return the sql instead of stdout

    Commands not implemented(yet):
        list_templates      
        edit

    AUTO-GENERATE NOT SUPPORTED
    """

    __config_attributes = [
        "script_location",
        "file_template",
        "timezone",
        "truncate_slug_length",
        "version_locations",
        "output_encoding",
        "attributes",
    ]

    __config_defaults = {
        "script_location": "moonshine_alembic",
        "file_template": "%%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d%%(second).2d_%%(rev)s_%%(slug)s",
        # "timezone": None,
        # "truncate_slug_length": 40,
        "version_locations": ["moonshine_alembic/versions"],
        # "output_encoding": "utf-8",
    }

    __config = None
    __engine = None
    __script_directory = None
    __environment_context = None

    target_metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    def __init__(self, config=None, engine=None, engine_config=None):
        if config is not None:
            self.config = config
        if engine is not None:
            self.engine = engine
        elif engine_config is not None:
            self.engine = engine_config
        # else:
        #     # This is only relevant for revision and merge
        #     self.engine = engine_from_config(
        #         {"sqlalchemy.url": "driver://user:pass@localhost/dbname"}
        #     )

        # determine logging configuration. Below flask-alembic loggers

        # # add logging handler if not configured
        # console_handler = logging.StreamHandler(sys.stderr)
        # console_handler.formatter = logging.Formatter(
        #     fmt="%(levelname)-5.5s [%(name)s] %(message)s", datefmt="%H:%M:%S"
        # )

        # sqlalchemy_logger = logging.getLogger("sqlalchemy")
        # alembic_logger = logging.getLogger("alembic")

        # if not sqlalchemy_logger.hasHandlers():
        #     sqlalchemy_logger.setLevel(logging.WARNING)
        #     sqlalchemy_logger.addHandler(console_handler)

        # # alembic adds a null handler, remove it
        # if len(alembic_logger.handlers) == 1 and isinstance(
        #     alembic_logger.handlers[0], logging.NullHandler
        # ):
        #     alembic_logger.removeHandler(alembic_logger.handlers[0])

        # if not alembic_logger.hasHandlers():
        #     alembic_logger.setLevel(logging.INFO)
        #     alembic_logger.addHandler(console_handler)

    @property
    def __default_config(self) -> Config:
        config = Config()
        for k, v in self.__config_defaults.items():
            if k == "version_locations":
                config.set_main_option(k, " ".join(list(v)))
            else:
                config.set_main_option(k, v)
        return config

    @property
    def config(self) -> Config:
        if isinstance(self.__config, Config):
            return self.__config
        # set default_config
        self.__config = self.__default_config
        return self.__config

    @config.setter
    def config(self, value):
        # load defaults
        config = self.__default_config
        if isinstance(value, Config):
            # replace config
            self.__config = value
        elif isinstance(value, dict):
            # Only allow prequalified attributes
            for attribute in self.__config_attributes:
                # load attribute values and overwite defaults
                attribute_value = value.get(attribute)
                if attribute_value is not None:
                    if attribute == "attributes" and isinstance(
                        attribute_value, dict
                    ):
                        for attr_k, attr_v in attribute_value.items():
                            config.attributes[attr_k] = attr_v  # noqa
                    elif attribute == "version_locations":
                        config.set_main_option(
                            attribute, " ".join(list(attribute_value))
                        )
                    else:
                        config.set_main_option(attribute, attribute_value)
        else:
            raise TypeError(f"Unsupported config type : {type(value)}")

        # set config
        self.__config = config

    @property
    def script_directory(self) -> ScriptDirectory:
        if isinstance(self.__script_directory, ScriptDirectory):
            return self.__script_directory
        self.__script_directory = ScriptDirectory.from_config(self.config)
        return self.__script_directory

    @property
    def engine(self):
        assert (
            self.__engine is not None
        ), "SQLAchemy Engine is not configured."
        return self.__engine

    @engine.setter
    def engine(self, value):
        if isinstance(value, Engine):
            self.__engine = value

        if isinstance(value, dict):
            self.__engine = engine_from_config(value)

    @property
    def environment_context(self) -> EnvironmentContext:
        if isinstance(self.__environment_context, EnvironmentContext):
            return self.__environment_context
        self.__environment_context = EnvironmentContext(
            self.config, self.script_directory
        )
        return self.__environment_context

    @property
    @contextmanager
    def migration_context(self):
        with self.engine.connect() as conn:
            env = self.environment_context
            env.configure(connection=conn)
            yield env.get_context()

    def get_template_directory(self):
        """Return the directory where Moonshine setup templates are found.

        This method is used by the moonshine ``init`` command.

        """
        package_dir = os.path.abspath(os.path.dirname(__file__))
        return os.path.join(package_dir, "templates")

    def init(self, template="moonshine_generic", package=False):
        """Initialize a new scripts directory.

        :param template: string name of the migration environment template to
        use.

        :param package: when True, write ``__init__.py`` files into the
        environment location as well as the versions/ location.

        .. versionadded:: 1.2


        """
        directory = self.config.get_main_option("script_location")

        if os.access(directory, os.F_OK) and os.listdir(directory):
            raise util.CommandError(
                "Directory %s already exists and is not empty" % directory
            )

        template_dir = os.path.join(self.get_template_directory(), template)
        if not os.access(template_dir, os.F_OK):
            raise util.CommandError("No such template %r" % template)

        if not os.access(directory, os.F_OK):
            util.status(
                "Creating directory %s" % os.path.abspath(directory),
                os.makedirs,
                directory,
            )

        versions = os.path.join(directory, "versions")
        util.status(
            "Creating directory %s" % os.path.abspath(versions),
            os.makedirs,
            versions,
        )

        script = ScriptDirectory(directory)

        for file_ in os.listdir(template_dir):
            file_path = os.path.join(template_dir, file_)
            if os.path.isfile(file_path):
                output_file = os.path.join(directory, file_)
                script._copy_file(file_path, output_file)

        if package:
            for path in [
                os.path.join(os.path.abspath(directory), "__init__.py"),
                os.path.join(os.path.abspath(versions), "__init__.py"),
            ]:
                file_ = util.status("Adding %s" % path, open, path, "w")
                file_.close()

    def revision(
        self,
        message=None,
        head="head",
        splice=False,
        branch_label=None,
        version_path=None,
        rev_id=None,
        depends_on=None,
        process_revision_directives=None,
    ):
        """Create a new revision file.

        :param message: string message to apply to the revision; this is the
        ``-m`` option to ``alembic revision``.

        :param head: head revision to build the new revision upon as a parent;
        this is the ``--head`` option to ``alembic revision``.

        :param splice: whether or not the new revision should be made into a
        new head of its own; is required when the given ``head`` is not itself
        a head.  This is the ``--splice`` option to ``alembic revision``.

        :param branch_label: string label to apply to the branch; this is the
        ``--branch-label`` option to ``alembic revision``.

        :param version_path: string symbol identifying a specific version path
        from the configuration; this is the ``--version-path`` option to
        ``alembic revision``.

        :param rev_id: optional revision identifier to use instead of having
        one generated; this is the ``--rev-id`` option to ``alembic revision``.

        :param depends_on: optional list of "depends on" identifiers; this is the
        ``--depends-on`` option to ``alembic revision``.

        :param process_revision_directives: this is a callable that takes the
        same form as the callable described at
        :paramref:`.EnvironmentContext.configure.process_revision_directives`;
        will be applied to the structure generated by the revision process
        where it can be altered programmatically.   Note that unlike all
        the other parameters, this option is only available via programmatic
        use of :func:`.command.revision`

        .. versionadded:: 0.9.0

        """
        command_args = dict(
            message=message,
            autogenerate=False,
            sql=False,
            head=head,
            splice=splice,
            branch_label=branch_label,
            version_path=version_path,
            rev_id=rev_id,
            depends_on=depends_on,
        )
        revision_context = autogenerate.RevisionContext(
            self.config,
            self.script_directory,
            command_args,
            process_revision_directives=process_revision_directives,
        )

        scripts = [script for script in revision_context.generate_scripts()]
        if len(scripts) == 1:
            return scripts[0]
        else:
            return scripts

    def merge(self, revisions, message=None, branch_label=None, rev_id=None):
        """Merge two revisions together.  Creates a new migration file.

        .. versionadded:: 0.7.0        

        :param message: string message to apply to the revision

        :param branch_label: string label name to apply to the new revision

        :param rev_id: hardcoded revision identifier instead of generating a new
        one.

        .. seealso::

            :ref:`branches`

        """

        return self.script_directory.generate_revision(
            rev_id or util.rev_id(),
            message,
            refresh=True,
            head=revisions,
            branch_labels=branch_label,
            config=self.config,
        )

    def upgrade(self, revision, sql=False, tag=None):
        """Upgrade to a later version.

        :param revision: string revision target or range for --sql mode

        :param sql: if True, use ``--sql`` mode

        :param tag: an arbitrary "tag" that can be intercepted by custom
        ``env.py`` scripts via the :meth:`.EnvironmentContext.get_tag_argument`
        method.

        """
        config = self.config
        script = self.script_directory
        config.attributes["engine"] = self.engine
        config.attributes["target_metadata"] = self.target_metadata

        output_buffer = io.StringIO()
        config.attributes["output_buffer"] = output_buffer

        starting_rev = None
        if ":" in revision:
            if not sql:
                raise util.CommandError("Range revision not allowed")
            starting_rev, revision = revision.split(":", 2)

        def do_upgrade(rev, context):
            return script._upgrade_revs(revision, rev)

        with EnvironmentContext(
            config,
            script,
            fn=do_upgrade,
            as_sql=sql,
            starting_rev=starting_rev,
            destination_rev=revision,
            tag=tag,
        ):
            script.run_env()
            output_buffer.seek(0)
            return output_buffer.read()

    def downgrade(self, revision, sql=False, tag=None):
        """Revert to a previous version.

        :param revision: string revision target or range for --sql mode

        :param sql: if True, use ``--sql`` mode

        :param tag: an arbitrary "tag" that can be intercepted by custom
        ``env.py`` scripts via the :meth:`.EnvironmentContext.get_tag_argument`
        method.

        """

        config = self.config
        script = self.script_directory
        config.attributes["engine"] = self.engine

        output_buffer = io.StringIO()
        config.attributes["output_buffer"] = output_buffer

        starting_rev = None
        if ":" in revision:
            if not sql:
                raise util.CommandError("Range revision not allowed")
            starting_rev, revision = revision.split(":", 2)
        elif sql:
            raise util.CommandError(
                "downgrade with --sql requires <fromrev>:<torev>"
            )

        def do_downgrade(rev, context):
            return script._downgrade_revs(revision, rev)

        with EnvironmentContext(
            config,
            script,
            fn=do_downgrade,
            as_sql=sql,
            starting_rev=starting_rev,
            destination_rev=revision,
            tag=tag,
        ):
            script.run_env()
            output_buffer.seek(0)
            return output_buffer.read()

    def show(self, revision):
        """Show the revision(s) denoted by the given symbol.
       
        :param revision: string revision target

        """
        script = self.script_directory
        return script.get_revisions(revision)

    def history(self, rev_range="base:heads", indicate_current=False):
        """List changeset scripts in chronological order.

        :param rev_range: string revision range

        :param indicate_current: indicate current revision.

        ..versionadded:: 0.9.9

        """

        if rev_range is not None:
            if ":" not in rev_range:
                raise util.CommandError(
                    "History range requires [start]:[end], "
                    "[start]:, or :[end]"
                )
            base, head = rev_range.strip().split(":")
        else:
            base = head = None

        environment = (
            util.asbool(self.config.get_main_option("revision_environment"))
            or indicate_current
        )

        def _display_history(base, head, currents=()):

            history = list()
            for sc in self.script_directory.walk_revisions(
                base=base or "base", head=head or "heads"
            ):
                if indicate_current:
                    sc._db_current_indicator = sc in currents
                history.insert(0, sc)

            return history

        def _display_history_w_current(base, head):
            def _display_current_history(rev):
                if head == "current":
                    return _display_history(base, rev, rev)
                elif base == "current":
                    return _display_history(rev, head, rev)
                else:
                    return _display_history(base, head, rev)
                return []

            rev = self.current
            return _display_current_history(rev)

        if base == "current" or head == "current" or environment:
            return _display_history_w_current(base, head)
        else:
            return _display_history(base, head)

    def heads(self, resolve_dependencies=False):
        """Show current available heads in the script directory.

        :param resolve_dependencies: treat dependency version as down revisions.
        """

        if resolve_dependencies:
            return self.script_directory.get_revisions("heads")

        return self.script_directory.get_revisions(
            self.script_directory.get_heads()
        )

    @property
    def branches(self):
        """Show current branch points."""
        script = self.script_directory
        branches = list()
        for sc in script.walk_revisions():
            if sc.is_branch_point:
                branches.append(sc)
        return branches

    @property
    def current(self):
        """Display the current revision for a database."""
        with self.migration_context as migration_context:
            return self.script_directory.get_revisions(
                migration_context.get_current_heads()
            )

    def stamp(self, revision, sql=False, tag=None, purge=False):
        """'stamp' the revision table with the given revision; don't
        run any migrations.

        :param revision: target revision or list of revisions.   May be a list
        to indicate stamping of multiple branch heads.

        .. note:: this parameter is called "revisions" in the command line
            interface.

        .. versionchanged:: 1.2  The revision may be a single revision or
            list of revisions when stamping multiple branch heads.

        :param sql: use ``--sql`` mode

        :param tag: an arbitrary "tag" that can be intercepted by custom
        ``env.py`` scripts via the :class:`.EnvironmentContext.get_tag_argument`
        method.

        :param purge: delete all entries in the version table before stamping.

        .. versionadded:: 1.2

        """

        config = self.config
        script = self.script_directory
        config.attributes["engine"] = self.engine

        output_buffer = io.StringIO()
        config.attributes["output_buffer"] = output_buffer

        starting_rev = None
        if sql:
            destination_revs = []
            for _revision in util.to_list(revision):
                if ":" in _revision:
                    srev, _revision = _revision.split(":", 2)

                    if starting_rev != srev:
                        if starting_rev is None:
                            starting_rev = srev
                        else:
                            raise util.CommandError(
                                "Stamp operation with --sql only supports a "
                                "single starting revision at a time"
                            )
                destination_revs.append(_revision)
        else:
            destination_revs = util.to_list(revision)

        def do_stamp(rev, context):
            return script._stamp_revs(util.to_tuple(destination_revs), rev)

        with EnvironmentContext(
            config,
            script,
            fn=do_stamp,
            as_sql=sql,
            starting_rev=starting_rev if sql else None,
            destination_rev=util.to_tuple(destination_revs),
            tag=tag,
            purge=purge,
        ):
            script.run_env()
            output_buffer.seek(0)
            return output_buffer.read()
