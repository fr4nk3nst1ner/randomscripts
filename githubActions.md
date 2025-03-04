

- `python-publish.yml`

```
name: Upload Python Package

on:
  release:
    types: [published]
  workflow_dispatch: 
    inputs:
      logLevel:
        description: 'Log level'
        required: true
        default: 'warning'
        type: choice
        options:
          - info
          - warning
          - debug
      tags:
        description: 'Test scenario tags'
        required: false
        type: boolean
      environment:
        description: 'Environment to run tests against'
        type: environment
        required: true

permissions:
  contents: write   

jobs:
  deploy:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: [3.9]

    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
        ref: main  #

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        python -m pip install setuptools wheel build bump2version
        python -m pip install -r requirements.txt  

    - name: Verify version before publishing
      run: python -c "import slackattack; print(slackattack.__version__)"

    - name: Set logging level
      run: |
        echo "Setting log level to ${{ github.event.inputs.logLevel }}"
      env:
        LOG_LEVEL: ${{ github.event.inputs.logLevel }}

    - name: Show current directory and files
      run: |
        pwd
        ls -alh

    - name: Extract current version
      id: get_version
      run: |
        VERSION=$(python get_version.py)
        echo "VERSION=$VERSION" >> $GITHUB_ENV
        echo "Current version: $VERSION"

    - name: Check if tag exists
      id: check_tag
      run: |
        if git rev-parse "${{ env.VERSION }}" >/dev/null 2>&1; then
          echo "Tag ${{ env.VERSION }} already exists."
          echo "tag_exists=true" >> $GITHUB_ENV
        else
          echo "Tag ${{ env.VERSION }} does not exist."
          echo "tag_exists=false" >> $GITHUB_ENV
        fi

    - name: Bump version and push to new branch
      if: env.tag_exists == 'false'
      run: |
        # Create a new branch for version bump
        git checkout -b version-bump-${{ env.VERSION }}
        bump2version patch --current-version ${{ env.VERSION }} --commit --tag --allow-dirty
        git push origin version-bump-${{ env.VERSION }} --tags
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    - name: Create Pull Request
      uses: peter-evans/create-pull-request@v4
      with:
        token: ${{ secrets.GITHUB_TOKEN }}
        branch: version-bump-v${{ env.VERSION }}
        base: main  
        title: "Version Bump to v${{ env.VERSION }}"
        body: "Automated version bump to v${{ env.VERSION }}"
        commit-message: "[create-pull-request] automated change"
        committer: "GitHub <noreply@github.com>"
        author: "fr4nk3nst1ner <fr4nk3nst1ner@users.noreply.github.com>"

    - name: Verify files
      run: |
        pwd
        ls -la

    - name: Check file permissions
      run: ls -la requirements.txt

    - name: Print Python version
      run: python --version

    - name: Clean build environment
      run: |
        rm -rf dist build

    - name: Verify version before publishing
      run: python -c "import slackattack; print(slackattack.__version__)"

    - name: Build package
      run: |
        python -m build --sdist --wheel --outdir dist --no-isolation
        python -m pip install .

    - name: Conditional step for tags
      if: ${{ github.event.inputs.tags == 'true' }}
      run: |
        echo "Running additional steps for tags scenario."

    - name: Publish package
      uses: pypa/gh-action-pypi-publish@27b31702a0e7fc50959f5ad993c78deac1bdfc29
      with:
        user: __token__
        password: ${{ secrets.PYPI_API_TOKEN }}
```

- `pylint.yml`

```
name: Pylint

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.8", "3.9", "3.10"]
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pylint
    - name: Analysing the code with pylint
      run: |
        pylint $(git ls-files '*.py')
```
