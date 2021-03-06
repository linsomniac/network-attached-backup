check:
	bash -c 'cd tests && exec make'
	pep8 --show-source lib/*.py lib/nabstorageplugins/*.py tests/*.py \
		bin/harness

commit: check
	git diff >/tmp/git-diff.out 2>&1
	git commit -a
	git push
