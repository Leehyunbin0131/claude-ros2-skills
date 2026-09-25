^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package thermal_interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Forthcoming
-----------
* ThermalReading: replace ``temperature_millic`` (milli-degrees Celsius) with
  ``temperature_c`` (degrees Celsius) and add ``valid``. This is a breaking
  change: consumers must read ``temperature_c`` and check ``valid``.

0.3.1 (2026-08-14)
------------------
* Document the ThermalReading units.

0.3.0 (2026-06-02)
------------------
* Add ThermalReading.
