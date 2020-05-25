"""Console script for moonshine."""
import sys
import click
from moonshine import Moonshine

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

"""
init
revision
merge
"""


@click.command()
@click.option(
    "-d",
    "--directory",
    default="moonshine_alembic",
    type=click.STRING,
    help="String path of the target directory. default=moonshine_alembic",
)
@click.option(
    "-t",
    "--template",
    default="moonshine_generic",
    type=click.STRING,
    help="Which Template to use. default=moonshine_generic",
)
@click.option(
    "-p",
    "--package",
    default=False,
    type=click.BOOL,
    is_flag=True,
    help="Whether to include __init__.py in directory. default=False",
)
def init(directory, template, package):
    moonshine = Moonshine(config={"script_location": directory})
    moonshine.init(template=template, package=package)


@click.command()
@click.option(
    "-d",
    "--directory",
    default="moonshine_alembic",
    type=click.STRING,
    help="String path of the target directory. default=moonshine_alembic",
)
@click.option(
    "-m",
    "--message",
    type=click.STRING,
    help="String path of the target directory",
)
@click.option(
    "--head",
    default="head",
    type=click.STRING,
    help="Head revision to build the new revision upon as a parent. default=head",
)
@click.option(
    "--splice",
    default=False,
    type=click.BOOL,
    is_flag=True,
    help="Whether or not the new revision should be made into a new head of its own. default=False",
)
@click.option(
    "--branch-label",
    type=click.STRING,
    help="String label to apply to the branch",
)
@click.option(
    "--version-path",
    type=click.STRING,
    help="String symbol identifying a specific version path from the configuration",
)
@click.option(
    "--rev-id",
    type=click.STRING,
    help="Optional revision identifier to use instead of having one generated",
)
@click.option(
    "--depends-on",
    type=click.STRING,
    help='Optional list of "depends on" identifiers',
)
def revision(
    directory,
    message=None,
    head="head",
    splice=False,
    branch_label=None,
    version_path=None,
    rev_id=None,
    depends_on=None,
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

      .. versionadded:: 0.9.0

    """

    moonshine = Moonshine(config={"script_location": directory})
    moonshine.revision(
        message=message,
        head=head,
        splice=splice,
        branch_label=branch_label,
        version_path=version_path,
        rev_id=rev_id,
        depends_on=depends_on,
    )


@click.group()
def main(args=None):
    pass


main.add_command(init)
main.add_command(revision)

if __name__ == "__main__":
    main()
