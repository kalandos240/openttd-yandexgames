'use strict';

// Compatibility entry point for release workflows created while the regression
// gate still used its earlier descriptive filename. Keep one implementation of
// the actual test in test-cold-start-idbfs-migration.cjs.
require('./test-cold-start-idbfs-migration.cjs');
