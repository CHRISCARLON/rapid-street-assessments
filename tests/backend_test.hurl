# test.hurl
# 10 USRNs × 5 repeats = 50 total requests
# run this test with "hurl --test --repeat 5 backend/backend_test.hurl"

GET http://localhost:8080/street-info-llm?usrn=23003630
HTTP 200

GET http://localhost:8080/street-info-llm?usrn=23007153
HTTP 200

GET http://localhost:8080/street-info-llm?usrn=23002897
HTTP 200

GET http://localhost:8080/street-info-llm?usrn=23000176
HTTP 200

GET http://localhost:8080/street-info-llm?usrn=23013760
HTTP 200

GET http://localhost:8080/street-info-llm?usrn=23009745
HTTP 200

GET http://localhost:8080/street-info-llm?usrn=23011275
HTTP 200

GET http://localhost:8080/street-info-llm?usrn=23008944
HTTP 200

GET http://localhost:8080/street-info-llm?usrn=23003630
HTTP 200

GET http://localhost:8080/street-info-llm?usrn=23007153
HTTP 200
