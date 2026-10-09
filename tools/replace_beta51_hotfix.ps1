# One-time Beta 5.1 Hotfix 1 replacement explicitly authorized by the owner.
$ErrorActionPreference = 'Stop'
$releaseId = 407938999
$oldTag = 'v1.0.0-beta.5.1'
$oldTagObject = '4590de9c41d5954541b5f34e6a05476a9eb6a4d2'
$baselineCommit = '95aeae14ce4f0466b58bf085f5d2c72088100362'
$oldAssets = @(
  @{id=625043334;name='Nioh-HinoEnma-1.0.0-beta.5.1-source.zip';size=552726;digest='sha256:8f53ac69663d2d59891bf9c47162806d4f77941d228b06d6a325c62e5f0cb594'},
  @{id=625043335;name='Nioh-HinoEnma-1.0.0-beta.5.1-windows-x64.exe';size=210944;digest='sha256:f8a91e5175d91fb5d17a31f9ceec7ba6ca1ea46f2fbc1e64d92e8c502d56b99c'}
)
function Api([string]$endpoint) {
  $raw = gh api $endpoint
  if ($LASTEXITCODE -ne 0) { throw "GitHub read failed: $endpoint" }
  return ($raw | ConvertFrom-Json)
}
function Require-Lease {
  if (git status --porcelain) { throw 'Source is not clean.' }
  if ((git rev-parse HEAD) -cne $env:GITHUB_SHA -or (git rev-parse 'HEAD^') -cne $baselineCommit) { throw 'Source parent or SHA changed.' }
  if ((Api "repos/$env:GITHUB_REPOSITORY/git/ref/heads/main").object.sha -cne $env:GITHUB_SHA) { throw 'Main changed during publication.' }
  $ref = Api "repos/$env:GITHUB_REPOSITORY/git/ref/tags/$oldTag"
  if ($ref.object.type -cne 'tag' -or $ref.object.sha -cne $oldTagObject) { throw 'Original Beta 5.1 tag changed.' }
}
function Save-Asset([long]$id, [string]$destination) {
  $process = [Diagnostics.Process]::new()
  $process.StartInfo.FileName = (Get-Command gh).Source
  $process.StartInfo.UseShellExecute = $false
  $process.StartInfo.CreateNoWindow = $true
  $process.StartInfo.RedirectStandardOutput = $true
  $process.StartInfo.RedirectStandardError = $true
  foreach ($argument in @('api', "repos/$env:GITHUB_REPOSITORY/releases/assets/$id", '--header', 'Accept: application/octet-stream')) { $process.StartInfo.ArgumentList.Add($argument) }
  $output = $null
  try {
    if (-not $process.Start()) { throw 'Asset download could not start.' }
    $errors = $process.StandardError.ReadToEndAsync()
    $output = [IO.File]::Create($destination)
    $process.StandardOutput.BaseStream.CopyTo($output)
    $output.Dispose(); $output = $null
    $process.WaitForExit()
    $null = $errors.GetAwaiter().GetResult()
    if ($process.ExitCode -ne 0) { throw 'Asset download failed.' }
  } finally {
    if ($null -ne $output) { $output.Dispose() }
    $process.Dispose()
  }
}
$v = Get-Content version.json -Raw | ConvertFrom-Json
if ($env:GITHUB_REPOSITORY -cne 'OIRANGEISHA/Nioh-HinoEnma' -or $env:GITHUB_REF -cne 'refs/heads/main' -or $v.version -cne '1.0.0-beta.5.1.hotfix.1' -or $v.tag -cne ('v' + $v.version) -or $v.release_owner -cne 'OIRANGEISHA' -or $v.channel -cne 'beta') { throw 'Not the single authorized Hotfix.' }
Require-Lease
$stem = 'Nioh-HinoEnma-' + $v.version
$manifest = Get-Content artifacts/release-manifest.json -Raw | ConvertFrom-Json
$tree = git rev-parse 'HEAD^{tree}'
if ($manifest.version -cne $v.version -or $manifest.source_commit -cne $env:GITHUB_SHA -or $manifest.source_tree -cne $tree -or @($manifest.assets).Count -ne 2) { throw 'Prepared source manifest differs.' }
$expectedNames = @("$stem-windows-x64.exe", "$stem-source.zip")
$local = @{}
$dist = @(Get-ChildItem -LiteralPath artifacts/dist -File)
if ($dist.Count -ne 2) { throw 'Prepared Release must contain exactly two files.' }
foreach ($file in $dist) {
  $record = @($manifest.assets | Where-Object name -CEQ $file.Name)
  $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($file.Name -cnotin $expectedNames -or $record.Count -ne 1 -or $record[0].sha256 -cne $hash -or $record[0].bytes -ne $file.Length) { throw 'Prepared asset differs.' }
  $local[$file.Name] = @{size=$file.Length;hash=$hash;path=$file.FullName}
}
function Check-Tag {
  $ref = Api "repos/$env:GITHUB_REPOSITORY/git/ref/tags/$($v.tag)"
  if ($ref.object.type -cne 'tag') { throw 'Hotfix tag is not annotated.' }
  $tag = Api "repos/$env:GITHUB_REPOSITORY/git/tags/$($ref.object.sha)"
  if ($tag.tag -cne $v.tag -or $tag.object.type -cne 'commit' -or $tag.object.sha -cne $env:GITHUB_SHA -or $tag.tagger.name -cne 'github-actions[bot]' -or $tag.tagger.email -cne '41898282+github-actions[bot]@users.noreply.github.com') { throw 'Hotfix tag differs from reviewed source/publisher.' }
  if ((Api "repos/$env:GITHUB_REPOSITORY/git/commits/$env:GITHUB_SHA").tree.sha -cne $tree) { throw 'Remote source tree differs.' }
  return $ref.object.sha
}
function Check-NewAssets([string]$phase, [bool]$onlyNew) {
  $release = Api "repos/$env:GITHUB_REPOSITORY/releases/$releaseId"
  if ($release.id -ne $releaseId -or $release.draft -or -not $release.prerelease -or $release.immutable -or $release.author.login -cne 'github-actions[bot]') { throw 'Release identity or mutable Pre-release state differs.' }
  $assets = @(Api "repos/$env:GITHUB_REPOSITORY/releases/$releaseId/assets?per_page=100")
  if ($onlyNew -and $assets.Count -ne 2) { throw 'Final Release must have exactly two assets.' }
  if (-not $onlyNew) {
    if ($assets.Count -ne 4) { throw 'Staged inventory must be original two plus new two.' }
    foreach ($old in $oldAssets) {
      $found = @($assets | Where-Object id -EQ $old.id)
      if ($found.Count -ne 1 -or $found[0].name -cne $old.name -or $found[0].digest -cne $old.digest -or $found[0].size -ne $old.size) { throw 'Staged original asset changed.' }
    }
  }
  $directory = 'artifacts/readback-' + $phase
  if (Test-Path -LiteralPath $directory) { throw 'Readback directory is not fresh.' }
  New-Item -ItemType Directory -Path $directory | Out-Null
  $ids = @{}
  foreach ($name in $expectedNames) {
    $matches = @($assets | Where-Object name -CEQ $name)
    if ($matches.Count -ne 1) { throw 'New asset missing or duplicate.' }
    $asset = $matches[0]; $expected = $local[$name]
    if ($asset.state -cne 'uploaded' -or $asset.uploader.login -cne 'github-actions[bot]' -or $asset.size -ne $expected.size -or $asset.digest -cne ('sha256:' + $expected.hash)) { throw 'New asset uploader/size/digest differs.' }
    $path = Join-Path $directory $name
    Save-Asset $asset.id $path
    if ((Get-Item -LiteralPath $path).Length -ne $expected.size -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expected.hash) { throw 'Downloaded asset bytes differ.' }
    $ids[$name] = $asset.id
  }
  $verificationOutput = python tools/package.py --source-commit "$env:GITHUB_SHA" --verify-source-zip (Join-Path $directory "$stem-source.zip") --exe (Join-Path $directory "$stem-windows-x64.exe")
  if ($LASTEXITCODE -ne 0) { throw 'Exact downloaded source ZIP or EXE evidence differs.' }
  $verification = $verificationOutput | ConvertFrom-Json
  if (-not $verification.source_archive_verified -or $verification.source_commit -cne $env:GITHUB_SHA -or $verification.executable_sha256 -cne $local["$stem-windows-x64.exe"].hash) { throw 'Source verifier output differs.' }
  return $ids
}
$notes = Get-Content -LiteralPath artifacts/release-notes.md -Raw
$title = 'Nioh Hino-Enma ' + $v.display_version
$release = Api "repos/$env:GITHUB_REPOSITORY/releases/$releaseId"
if ($release.tag_name -ceq $v.tag) {
  Check-Tag | Out-Null
  Check-NewAssets 'already-published' $true | Out-Null
  if ($release.name -cne $title -or $release.target_commitish -cne $env:GITHUB_SHA -or $release.body.TrimEnd() -cne $notes.TrimEnd()) { throw 'Existing Hotfix differs.' }
  'This exact Hotfix has already replaced Beta 5.1; nothing was changed.' >> $env:GITHUB_STEP_SUMMARY
  exit 0
}
if ($release.id -ne $releaseId -or $release.tag_name -cne $oldTag -or $release.draft -or $release.immutable -or -not $release.prerelease -or $release.author.login -cne 'github-actions[bot]' -or $release.target_commitish -cne $baselineCommit) { throw 'Original Release lease mismatch.' }
$existing = @(Api "repos/$env:GITHUB_REPOSITORY/releases/$releaseId/assets?per_page=100")
foreach ($old in $oldAssets) {
  $found = @($existing | Where-Object id -EQ $old.id)
  if ($found.Count -ne 1 -or $found[0].name -cne $old.name -or $found[0].size -ne $old.size -or $found[0].digest -cne $old.digest) { throw 'Original asset lease mismatch.' }
}
if ($existing.Count -ne 2) { throw 'Original Release inventory changed; inspect before retry.' }
$release | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath artifacts/beta51-before-hotfix.json -Encoding utf8
$remoteTag = git ls-remote origin "refs/tags/$($v.tag)"
if ($LASTEXITCODE -ne 0) { throw 'Tag read failed.' }
if (-not $remoteTag) {
  git config user.name 'github-actions[bot]'
  git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
  git tag -a "$($v.tag)" "$env:GITHUB_SHA" -m "$title; Release Owner OIRANGEISHA; explicitly authorized Beta 5.1 replacement"
  if ($LASTEXITCODE -ne 0) { throw 'Annotated tag creation failed.' }
  git push --atomic origin "refs/tags/$($v.tag)"
  if ($LASTEXITCODE -ne 0) { throw 'Annotated tag push failed.' }
}
$tagObject = Check-Tag
$bundle = Get-Content -LiteralPath artifacts/hotfix-attestation.jsonl -Raw | ConvertFrom-Json
$statement = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($bundle.dsseEnvelope.payload)) | ConvertFrom-Json
if ($statement.predicateType -cne 'https://slsa.dev/provenance/v1' -or @($statement.subject).Count -ne 2) { throw 'Attestation type or subject count differs.' }
$subjectNames = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($subject in $statement.subject) {
  $name = [IO.Path]::GetFileName($subject.name)
  if (-not $local.ContainsKey($name) -or -not $subjectNames.Add($name) -or $subject.digest.sha256 -cne $local[$name].hash) { throw 'Attested asset differs.' }
}
$workflow = $statement.predicate.buildDefinition.externalParameters.workflow
$dependencies = @($statement.predicate.buildDefinition.resolvedDependencies | Where-Object { $_.digest.gitCommit -ceq $env:GITHUB_SHA -and $_.uri -clike "git+https://github.com/$env:GITHUB_REPOSITORY@*" })
if ($workflow.repository -cne "https://github.com/$env:GITHUB_REPOSITORY" -or $workflow.path -cne '.github/workflows/hotfix.yml' -or $workflow.ref -cne 'refs/heads/main' -or $dependencies.Count -ne 1) { throw 'Attestation source or workflow differs.' }
Require-Lease
$paths = @($dist | ForEach-Object FullName)
gh release upload "$oldTag" @paths --repo "$env:GITHUB_REPOSITORY"
if ($LASTEXITCODE -ne 0) { throw 'Upload failed; old assets retained. Inspect before retry.' }
Write-Host 'Phase: new assets uploaded; original Release metadata and old assets retained.'
$newIds = Check-NewAssets 'staged' $false
Require-Lease
$release = Api "repos/$env:GITHUB_REPOSITORY/releases/$releaseId"
if ($release.tag_name -cne $oldTag -or $release.id -ne $releaseId) { throw 'Release changed after upload.' }
$patch = @{tag_name=$v.tag;target_commitish=$env:GITHUB_SHA;name=$title;body=$notes;draft=$false;prerelease=$true;make_latest='false'}
$patch | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath artifacts/hotfix-release-update.json -Encoding utf8
gh api --method PATCH "repos/$env:GITHUB_REPOSITORY/releases/$releaseId" --input artifacts/hotfix-release-update.json | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Release update failed; old assets retained.' }
$updated = Api "repos/$env:GITHUB_REPOSITORY/releases/$releaseId"
if ($updated.id -ne $releaseId -or $updated.tag_name -cne $v.tag -or $updated.name -cne $title -or $updated.target_commitish -cne $env:GITHUB_SHA -or $updated.body.TrimEnd() -cne $notes.TrimEnd()) { throw 'Updated Release readback differs; old assets retained.' }
Write-Host 'Phase: same Release updated to Hotfix; old assets retained until cleanup verification.'
Require-Lease
if ((Check-Tag) -cne $tagObject) { throw 'Hotfix tag changed.' }
$remainingOld = [Collections.Generic.HashSet[long]]::new()
foreach ($old in $oldAssets) { $null = $remainingOld.Add($old.id) }
function Assert-Published-Inventory {
  $current = Api "repos/$env:GITHUB_REPOSITORY/releases/$releaseId"
  if ($current.id -ne $releaseId -or $current.tag_name -cne $v.tag -or $current.name -cne $title -or $current.draft -or -not $current.prerelease -or $current.immutable -or $current.target_commitish -cne $env:GITHUB_SHA -or $current.body.TrimEnd() -cne $notes.TrimEnd()) { throw 'Updated Release changed before cleanup.' }
  $inventory = @(Api "repos/$env:GITHUB_REPOSITORY/releases/$releaseId/assets?per_page=100")
  if ($inventory.Count -ne (2 + $remainingOld.Count)) { throw 'Cleanup asset count changed.' }
  foreach ($name in $expectedNames) {
    $found = @($inventory | Where-Object name -CEQ $name)
    if ($found.Count -ne 1 -or $found[0].id -ne $newIds[$name] -or $found[0].state -cne 'uploaded' -or $found[0].uploader.login -cne 'github-actions[bot]' -or $found[0].size -ne $local[$name].size -or $found[0].digest -cne ('sha256:' + $local[$name].hash)) { throw 'Verified new asset changed before cleanup.' }
  }
  foreach ($oldRecord in $oldAssets) {
    if ($remainingOld.Contains($oldRecord.id)) {
      $found = @($inventory | Where-Object id -EQ $oldRecord.id)
      if ($found.Count -ne 1 -or $found[0].name -cne $oldRecord.name -or $found[0].size -ne $oldRecord.size -or $found[0].digest -cne $oldRecord.digest) { throw 'Original asset changed before cleanup.' }
    }
  }
}
foreach ($old in $oldAssets) {
  Require-Lease
  Assert-Published-Inventory
  $asset = Api "repos/$env:GITHUB_REPOSITORY/releases/assets/$($old.id)"
  if ($asset.id -ne $old.id -or $asset.name -cne $old.name -or $asset.digest -cne $old.digest) { throw 'Old asset changed before authorized removal.' }
  gh api --method DELETE "repos/$env:GITHUB_REPOSITORY/releases/assets/$($old.id)"
  if ($LASTEXITCODE -ne 0) { throw 'Old asset removal failed; inspect the Release inventory.' }
  $null = $remainingOld.Remove($old.id)
  Write-Host "Authorized old asset removed: $($old.id); old assets remaining: $($remainingOld.Count)."
}
Assert-Published-Inventory
$finalIds = Check-NewAssets 'published' $true
foreach ($name in $expectedNames) { if ($finalIds[$name] -ne $newIds[$name]) { throw 'New asset identity changed.' } }
Require-Lease
Assert-Published-Inventory
if ((Check-Tag) -cne $tagObject) { throw 'Final Hotfix tag object changed.' }
$finalRelease = Api "repos/$env:GITHUB_REPOSITORY/releases/$releaseId"
if ($finalRelease.author.login -cne 'github-actions[bot]' -or -not $finalRelease.published_at) { throw 'Final Release publisher or publication timestamp differs.' }
"Hotfix replaced the same Release ${releaseId}: $($finalRelease.html_url). Exactly EXE and source ZIP; downloaded hashes, source and attestation matched. Old annotated tag preserved." >> $env:GITHUB_STEP_SUMMARY
