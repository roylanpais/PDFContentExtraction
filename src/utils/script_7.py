# Let's run the tests to validate our pipeline
exec(open("test_extraction.py").read())

# Run the test suite
success = run_tests()