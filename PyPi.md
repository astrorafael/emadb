# Uploading to PyPi

How to upload a new package release into PyPi

1. List your current tags

	`git tag`

2. tag the current X.Y.Z release. We use the annotated tags
to upload them to GitHub and mark releases there as well.

	- If it is a bug, then increment Z. 
	- If it is a minor change (new feature), then increment Y
	
	`git tag -a  X.Y.Z`

3. Register the new release in PyPi

	`python setup.py register` 
	
4. Package and Upload at the same time 

	`sudo python setup.py sdist upload`

