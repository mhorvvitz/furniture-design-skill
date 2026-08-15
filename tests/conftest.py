import pytest
from carcass import Carcass


@pytest.fixture
def demo_spec():
    """800x1800x400 cabinet: sides, top, bottom, 2 shelves, 2 doors, 1 rod.
    Built with the documented convention: front = Z = D."""
    c = Carcass(800, 1800, 400, t=18, name="Demo")
    c.sides()
    c.bottom()
    c.top()
    c.shelves(2, y0=18, y1=1782)
    c.rod(y=1500)
    c.door(y0=18, y1=1782, leaves=2)
    return c.spec()
