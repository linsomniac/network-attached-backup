check:
	python tests/model.py
	pep8 --show-source lib/nabdb.py
	pep8 --show-source lib/nabmodel.py
	pep8 --show-source lib/nabsupp.py
	pep8 --show-source tests/model.py
	pep8 --show-source bin/harness

commit: check
	git diff >/tmp/git-diff.out 2>&1
	git commit -a
	git push
