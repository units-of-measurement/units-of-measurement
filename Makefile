SHEETS = units/resources/si_input.csv

units/resources/si_input.csv:
	curl -L -o $@ "https://docs.google.com/spreadsheets/d/1AlKZIauwtQNg49ujaoD4OL_kTs1Is0-NlEqTvoR2a_o/export?format=csv&gid=214313365"

.PHONY: refresh_sheets
refresh_sheets:
	rm -rf $(SHEETS)
	make $(SHEETS)
