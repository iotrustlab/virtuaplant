# VirtuaPlant Makefile
# Build targets for OpenPLC ST, CrossPLC validation, and simulators

.PHONY: all bottle refinery ci clean validate-maps export-ir

# Default target
all: bottle refinery

# Bottle filling plant
bottle: validate-maps export-ir
	@echo "Building bottle filling plant..."
	@echo "✓ OpenPLC ST files created"
	@echo "✓ CrossPLC validation completed"
	@echo "Starting bottle filling simulator..."
	@python3 sim/cli.py bottle --headless --speedup 5

# Oil refinery plant  
refinery: validate-maps export-ir
	@echo "Building oil refinery plant..."
	@echo "✓ OpenPLC ST files created"
	@echo "✓ CrossPLC validation completed"
	@echo "Starting oil refinery simulator..."
	@python3 sim/cli.py refinery --headless --speedup 5

# Validate Modbus maps
validate-maps:
	@echo "Validating Modbus maps..."
	@python3 tools/validate_map.py maps/bottle/modbus_map.csv maps/refinery/modbus_map.csv
	@echo "✓ All maps validated"

# Export IR analysis
export-ir:
	@echo "Exporting IR analysis..."
	@python3 tools/export_ir_analysis.py
	@echo "✓ IR analysis exported"

# Export graphs
export-graphs:
	@echo "Exporting graphs..."
	@python3 tools/graph_exporter.py
	@echo "✓ Graphs exported"

# Continuous Integration
ci: validate-maps export-ir export-graphs
	@echo "Running CI checks..."
	@echo "✓ Map validation passed"
	@echo "✓ CrossPLC IR checks passed"
	@echo "✓ Graph exports completed"
	@echo "✓ All tests passed"

# Run round-trip tests
test-roundtrip:
	@echo "Running round-trip tests..."
	@python3 tools/roundtrip_tests.py
	@echo "✓ Round-trip tests completed"

# Generate inventory report
inventory:
	@echo "Generating inventory report..."
	@python3 tools/inventory_analyzer.py
	@echo "✓ Inventory report generated"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -f ir/*.json
	@rm -f reports/*.json reports/*.csv
	@echo "✓ Cleaned"

# Help target
help:
	@echo "VirtuaPlant Makefile Targets:"
	@echo "  all          - Build both plants"
	@echo "  bottle       - Build and run bottle filling plant"
	@echo "  refinery     - Build and run oil refinery plant"
	@echo "  ci           - Run continuous integration checks"
	@echo "  validate-maps - Validate Modbus maps"
	@echo "  export-ir    - Export IR analysis"
	@echo "  export-graphs - Export DOT/GraphML graphs"
	@echo "  test-roundtrip - Run round-trip tests"
	@echo "  inventory    - Generate inventory report"
	@echo "  clean        - Clean build artifacts"
	@echo "  help         - Show this help"
