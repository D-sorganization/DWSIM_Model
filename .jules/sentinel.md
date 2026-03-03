# Security Audit Report

## Summary

- **High Severity**: 0
- **Medium Severity**: 0
- **Low Severity**: 2

## Details

### LOW Severity - src/dwsim_model/gasification.py:72
- **Issue**: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- **Code**: `71         """Sets up thermodynamics and compounds. DbC: Builder must exist."""
72         assert self.builder is not None, "Builder instance required"
73`

### LOW Severity - src/dwsim_model/gasification.py:209
- **Issue**: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- **Code**: `208         """Execute the configured flowsheet."""
209         assert self._is_built, "Flowsheet must be built before running"
210         self.builder.calculate()`
