Solar game
==========

Solar system simulation:

.. code:: bash

   python -m solar -c examples/sol.toml

Four body simulation:

.. code:: bash

   python -m solar -c examples/four-body.toml

Generate a config dynamically with the number of bodies, speeds, and
distance from the centre-of-mass:

.. code:: bash

   # 8 bodies, speed 0.01 AU / day, centre-of-mass distance 5.0 AU
   python configs/main.py --speed 0.01 --distance 5.0 8 - | python -m solar --config -
