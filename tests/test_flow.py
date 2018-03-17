import datetime

import pytest

import prefect
import ujson
from prefect.flow import Flow
from prefect.task import Task, Parameter
from prefect.signals import PrefectError
from prefect.tasks.core.function_task import FunctionTask
from prefect.utilities.tasks import task
from prefect.utilities.tests import DummyTask


class AddTask(Task):

    def run(self, x, y):
        return x + y


@pytest.fixture
def add_flow():
    with Flow() as f:
        x = Parameter('x')
        y = Parameter('y', default=10)
        z = AddTask()
        f.set_dependencies(z, keyword_results=dict(x=x, y=y))
    return f


def test_create_flow():
    # name is not required
    Flow()


def test_equality():
    f1 = Flow(name='hi', version=1)
    f2 = Flow(name='hi', version=1)
    assert f1 == f2
    f1.add_task(Task())
    assert f1 != f2


def test_add_task():
    f = Flow()
    t = Task()
    f.add_task(t)
    assert t in f.tasks


def test_add_task_wrong_type():
    f = Flow()

    with pytest.raises(TypeError):
        f.add_task(1)


def test_add_task_duplicate():
    f = Flow()
    t = Task()
    f.add_task(t)
    with pytest.raises(ValueError):
        f.add_task(t)


def test_context_manager():
    with Flow() as f1:
        with Flow() as f2:
            t2 = Task()
        t1 = Task()

    assert t1 in f1.tasks
    assert t2 in f2.tasks
    assert t2 not in f1.tasks
    assert t1 not in f2.tasks


def test_edge():
    f = Flow()
    t1 = Task()
    t2 = Task()
    f.add_edge(upstream_task=t1, downstream_task=t2)
    assert f.upstream_tasks(t2) == set([t1])
    assert f.upstream_tasks(t1) == set()
    assert f.downstream_tasks(t2) == set()
    assert f.downstream_tasks(t1) == set([t2])
    assert f.edges_to(t2) == f.edges_from(t1)


def test_iter():
    """
    Tests that iterating over a Flow yields the tasks in order
    """
    with Flow('test') as f:
        t1 = Task()
        t2 = Task()
        f.add_edge(upstream_task=t2, downstream_task=t1)
    assert tuple(f) == f.sorted_tasks() == (t2, t1)


def test_detect_cycle():
    f = Flow()
    t1 = Task()
    t2 = Task()
    t3 = Task()

    f.add_edge(t1, t2)
    f.add_edge(t2, t3)
    with pytest.raises(ValueError):
        f.add_edge(t3, t1)


def test_root_tasks():
    with Flow() as f:
        t1 = Task()
        t2 = Task()
        t3 = Task()

    f.add_edge(t1, t2)
    f.add_edge(t2, t3)

    assert f.root_tasks() == set([t1])


def test_terminal_tasks():
    with Flow() as f:
        t1 = Task()
        t2 = Task()
        t3 = Task()

    f.add_edge(t1, t2)
    f.add_edge(t2, t3)

    assert f.terminal_tasks() == set([t3])


def test_merge():
    f1 = Flow()
    f2 = Flow()

    t1 = Task()
    t2 = Task()
    t3 = Task()

    f1.add_edge(t1, t2)
    f2.add_edge(t2, t3)

    f2.update(f1)
    assert f2.tasks == set([t1, t2, t3])
    assert len(f2.edges) == 2


def test_serialize(add_flow):
    serialized = add_flow.serialize()
    assert serialized['id'] == add_flow.id
    assert serialized['name'] == add_flow.name
    assert serialized['version'] == add_flow.version
    assert len(serialized['tasks']) == 3
    assert len(serialized['edges']) == 2


def test_deserialize(add_flow):
    serialized = add_flow.serialize()
    f = Flow.deserialize(serialized)
    assert f.id == add_flow.id
    assert f.name == add_flow.name
    assert f.version == add_flow.version
    assert f.parameters() == add_flow.parameters()
    assert [t.id for t in f] == [t.id for t in add_flow]
    assert len(f.tasks) == 3
    assert len(f.edges) == 2
