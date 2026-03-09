# Security Audit Report

## Summary

- **High Severity**: 0
- **Medium Severity**: 0
- **Low Severity**: 5

## Details

### LOW Severity - src/dwsim_model/chemistry/reactions.py:281
- **Issue**: Try, Except, Pass detected.
- **Code**: `280                     trc_obj.SetPropertyValue(prop, val)
281                 except Exception:
282                     pass
283 `

### LOW Severity - src/dwsim_model/core.py:99
- **Issue**: Try, Except, Pass detected.
- **Code**: `98                     obj.GraphicObject.ShowObjectData = True
99                 except Exception:
100                     pass
101 `

### LOW Severity - src/dwsim_model/gui/tabs/results_tab.py:146
- **Issue**: Consider possible security implications associated with the subprocess module.
- **Code**: `145         """Open the results folder in the OS file manager."""
146         import subprocess
147         import sys
`

### LOW Severity - src/dwsim_model/results/extractor.py:249
- **Issue**: Try, Except, Pass detected.
- **Code**: `248                 return float(val)
249         except Exception:
250             pass
251         try:
`

### LOW Severity - src/dwsim_model/results/extractor.py:255
- **Issue**: Try, Except, Pass detected.
- **Code**: `254                 return float(val)
255         except Exception:
256             pass
257         return default
`
