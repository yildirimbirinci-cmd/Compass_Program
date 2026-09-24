/* Compass GLB Conversion Engine v0.6.4-p4
   Runs under 3dsmaxbatch.exe. Phase 1: scene analysis + FBX export.
*/
fn jsonEscape s = (
    local t = substituteString (s as string) "\\" "\\\\"
    t = substituteString t "\"" "\\\""
    t = substituteString t "\r" "\\r"
    substituteString t "\n" "\\n"
)

fn readAllText p = (
    local f = openFile p mode:"rt"
    if f == undefined then throw ("Cannot open job file: " + p)
    local txt = ""
    while not eof f do txt += (readLine f) + "\n"
    close f
    txt
)

fn getJsonString txt key = (
    local token = "\"" + key + "\""
    local p = findString txt token
    if p == undefined then return undefined
    local tail = substring txt (p + token.count) (txt.count - (p + token.count) + 1)
    local c = findString tail ":"
    if c == undefined then return undefined
    local start = p + token.count + c
    while start <= txt.count and (substring txt start 1) != "\"" do start += 1
    if start > txt.count then return undefined
    start += 1
    local stop = start
    while stop <= txt.count do (
        if (substring txt stop 1) == "\"" and (stop == start or (substring txt (stop-1) 1) != "\\") then exit
        stop += 1
    )
    local value = substring txt start (stop-start)
    value = substituteString value "\\\\" "\\"
    substituteString value "\\\"" "\""
)

global COMPASS_TEXTURE_RECORDS = #()

fn safeClassName v = (try ((classof v) as string) catch "Unknown")

fn appendUniqueString values value = (
    if value != undefined and value != "" and (findItem values value) == 0 do append values value
    values
)

fn writeTextureManifest path records = (
    local f = createFile path
    if f == undefined then throw ("Cannot create texture manifest: " + path)
    format "{\n  \"materials\": [\n" to:f
    for i = 1 to records.count do (
        local rec = records[i]
        if i > 1 do format ",\n" to:f
        format "    {\"material\": \"%\", \"texture\": \"%\"}" (jsonEscape rec[1]) (jsonEscape rec[2]) to:f
    )
    format "\n  ]\n}\n" to:f
    close f
)

fn collectMaterialClasses = (
    local names = #()
    for m in scenematerials where m != undefined do (
        local n = safeClassName m
        if findItem names n == 0 do append names n
    )
    names
)

fn collectRendererHints matClasses = (
    local hasCorona = false
    local hasVray = false
    for n in matClasses do (
        local l = toLower n
        if matchPattern l pattern:"*corona*" do hasCorona = true
        if matchPattern l pattern:"*vray*" do hasVray = true
    )
    #(hasCorona, hasVray)
)

fn writeReport path source matClasses hints geometryCount missingCount = (
    local f = createFile path
    if f == undefined then throw ("Cannot create report file: " + path)
    format "{\n" to:f
    format "  \"source\": \"%\",\n" (jsonEscape source) to:f
    format "  \"max_version\": \"%\",\n" (jsonEscape (maxVersion() as string)) to:f
    format "  \"geometry_count\": %,\n" geometryCount to:f
    format "  \"material_count\": %,\n" scenematerials.count to:f
    format "  \"uses_corona\": %,\n" (if hints[1] then "true" else "false") to:f
    format "  \"uses_vray\": %,\n" (if hints[2] then "true" else "false") to:f
    format "  \"missing_asset_count\": %,\n" missingCount to:f
    format "  \"material_classes\": [" to:f
    for i = 1 to matClasses.count do (
        if i > 1 do format ", " to:f
        format "\"%\"" (jsonEscape matClasses[i]) to:f
    )
    format "]\n}\n" to:f
    close f
)



fn safeGetProperty objectValue propertyName defaultValue = (
    local value = defaultValue
    try (
        if isProperty objectValue propertyName do value = getProperty objectValue propertyName
    ) catch()
    value
)

fn firstMaterialColor sourceMaterial = (
    local result = color 128 128 128
    if sourceMaterial == undefined then return result
    local candidates = #(#diffuse, #diffuseColor, #baseColor, #color, #colorDiffuse)
    for propertyName in candidates while result == (color 128 128 128) do (
        local value = safeGetProperty sourceMaterial propertyName undefined
        if value != undefined and isKindOf value Color do result = value
    )
    result
)

fn normalizedTexturePath mapValue = (
    if mapValue == undefined then return ""
    local candidates = #(
        #filename, #fileName, #file, #path, #mapName, #bitmapPath,
        #HDRIMapName, #hdriMapName, #sourceFile, #imageFile, #assetFileName
    )
    local rawPaths = #()
    for propertyName in candidates do (
        local value = safeGetProperty mapValue propertyName undefined
        if value != undefined do (
            local rawPath = ""
            try (rawPath = value as string) catch()
            if rawPath != "" and rawPath != "undefined" do appendUniqueString rawPaths rawPath
        )
    )

    -- Renderer maps sometimes expose the path only through an AssetUser value.
    local properties = #()
    try (properties = getPropNames mapValue) catch()
    for propertyName in properties do (
        local propertyText = toLower (propertyName as string)
        local pathLike = ((findString propertyText "file") != undefined) or ((findString propertyText "path") != undefined) or ((findString propertyText "mapname") != undefined)
        if pathLike do (
            local value = safeGetProperty mapValue propertyName undefined
            if value != undefined do (
                local rawPath = ""
                try (rawPath = value as string) catch()
                if rawPath != "" and rawPath != "undefined" do appendUniqueString rawPaths rawPath
            )
        )
    )

    for rawPath in rawPaths do (
        local candidatesToCheck = #(rawPath)
        try (
            local resolved = pathConfig.resolvePath rawPath
            if resolved != undefined and resolved != "" do appendUniqueString candidatesToCheck resolved
        ) catch()
        if maxFilePath != undefined and maxFilePath != "" do (
            appendUniqueString candidatesToCheck (maxFilePath + rawPath)
            appendUniqueString candidatesToCheck (maxFilePath + getFilenameFile rawPath + getFilenameType rawPath)
        )
        for candidate in candidatesToCheck where doesFileExist candidate do return candidate
    )
    ""
)

fn isBitmapLikeMap mapValue = (
    if mapValue == undefined then return false
    local pathValue = normalizedTexturePath mapValue
    if pathValue == "" then return false
    local mapSuper = undefined
    try (mapSuper = superClassOf mapValue) catch()
    mapSuper == textureMap
)

fn getSubTexmapCountSafe ownerValue = (
    local count = 0
    if ownerValue == undefined then return count
    try (count = getNumSubTexmaps ownerValue) catch()
    count
)

fn getSubTexmapSafe ownerValue index = (
    local value = undefined
    try (value = getSubTexmap ownerValue index) catch()
    value
)

fn getSubTexmapSlotNameSafe ownerValue index = (
    local value = ""
    try (value = getSubTexmapSlotName ownerValue index) catch()
    if value == undefined then value = ""
    try (value = value as string) catch (value = "")
    value
)

fn findBitmapInMap mapValue depth:0 = (
    if mapValue == undefined or depth > 16 then return undefined
    if isBitmapLikeMap mapValue do return mapValue

    -- Renderer maps frequently hide their children behind sub-texmap slots
    -- rather than public properties. CoronaLegacyMtl/CoronaBitmap pipelines
    -- depend on this API in 3ds Max 2020.
    local subCount = getSubTexmapCountSafe mapValue
    for index = 1 to subCount do (
        local childMap = getSubTexmapSafe mapValue index
        if childMap != undefined do (
            local found = findBitmapInMap childMap depth:(depth + 1)
            if found != undefined do return found
        )
    )

    local properties = #()
    try (properties = getPropNames mapValue) catch()
    for propertyName in properties do (
        local child = undefined
        try (child = getProperty mapValue propertyName) catch()
        if child != undefined do (
            local childSuper = undefined
            try (childSuper = superClassOf child) catch()
            if childSuper == textureMap then (
                local found = findBitmapInMap child depth:(depth + 1)
                if found != undefined do return found
            ) else if isKindOf child Array then (
                for arrayItem in child do (
                    local itemSuper = undefined
                    try (itemSuper = superClassOf arrayItem) catch()
                    if itemSuper == textureMap do (
                        local found = findBitmapInMap arrayItem depth:(depth + 1)
                        if found != undefined do return found
                    )
                )
            )
        )
    )
    undefined
)

fn slotLooksLikeBaseColor slotName = (
    local text = toLower slotName
    ((findString text "diffuse") != undefined) or
    ((findString text "albedo") != undefined) or
    ((findString text "base") != undefined) or
    ((findString text "color") != undefined)
)

fn findDiffuseBitmap sourceMaterial = (
    if sourceMaterial == undefined then return undefined
    local preferred = #(
        #diffuseMap, #texmapDiffuse, #baseMap, #baseTexmap,
        #texmapBase, #mapM1, #map1, #baseColorMap, #texmapBaseColor,
        #baseColorTexmap, #albedoMap, #texmapAlbedo,
        #texmapDiffuseOn, #texmapBaseColorOn
    )
    for propertyName in preferred do (
        local mapValue = safeGetProperty sourceMaterial propertyName undefined
        if mapValue != undefined do (
            local found = findBitmapInMap mapValue
            if found != undefined do return found
        )
    )

    -- First inspect named sub-texmap slots. This is the reliable route for
    -- CoronaLegacyMtl where diffuse/albedo maps are not always exposed by
    -- getPropNames or have renderer-version-specific property names.
    local subCount = getSubTexmapCountSafe sourceMaterial
    for index = 1 to subCount do (
        local slotName = getSubTexmapSlotNameSafe sourceMaterial index
        if slotLooksLikeBaseColor slotName do (
            local mapValue = getSubTexmapSafe sourceMaterial index
            local found = findBitmapInMap mapValue
            if found != undefined do (
                format "COMPASS_ENGINE: Base texture slot matched | material=% | slot=% | index=%\n" (safeGetProperty sourceMaterial #name "") slotName index
                return found
            )
        )
    )

    local properties = #()
    try (properties = getPropNames sourceMaterial) catch()
    for propertyName in properties do (
        local propertyText = toLower (propertyName as string)
        local isBaseProperty = ((findString propertyText "diffuse") != undefined) or ((findString propertyText "albedo") != undefined) or ((findString propertyText "base") != undefined) or ((findString propertyText "color") != undefined)
        if isBaseProperty do (
            local mapValue = safeGetProperty sourceMaterial propertyName undefined
            if mapValue != undefined do (
                local mapSuper = undefined
                try (mapSuper = superClassOf mapValue) catch()
                if mapSuper == textureMap do (
                    local found = findBitmapInMap mapValue
                    if found != undefined do return found
                )
            )
        )
    )

    -- Last resort: inspect every sub-texmap, then every texture property.
    -- This still prefers an actual file-backed texture and avoids procedural
    -- maps that cannot be represented by FBX/GLB.
    for index = 1 to subCount do (
        local mapValue = getSubTexmapSafe sourceMaterial index
        local found = findBitmapInMap mapValue
        if found != undefined do (
            local slotName = getSubTexmapSlotNameSafe sourceMaterial index
            format "COMPASS_ENGINE: Fallback texture slot matched | material=% | slot=% | index=%\n" (safeGetProperty sourceMaterial #name "") slotName index
            return found
        )
    )
    for propertyName in properties do (
        local mapValue = safeGetProperty sourceMaterial propertyName undefined
        if mapValue != undefined do (
            local mapSuper = undefined
            try (mapSuper = superClassOf mapValue) catch()
            if mapSuper == textureMap then (
                local found = findBitmapInMap mapValue
                if found != undefined do return found
            )
        )
    )
    undefined
)

fn makeFbxBitmap sourceMap = (
    local sourcePath = normalizedTexturePath sourceMap
    if sourcePath == "" then return undefined
    local result = undefined
    try (
        result = bitmapTexture filename:sourcePath
        result.name = "COMPASS_" + getFilenameFile sourcePath
        try (result.coords.U_Tiling = sourceMap.coords.U_Tiling) catch()
        try (result.coords.V_Tiling = sourceMap.coords.V_Tiling) catch()
        try (result.coords.U_Offset = sourceMap.coords.U_Offset) catch()
        try (result.coords.V_Offset = sourceMap.coords.V_Offset) catch()
        try (result.coords.W_Angle = sourceMap.coords.W_Angle) catch()
    ) catch (
        result = undefined
    )
    result
)

fn convertMaterialForExport sourceMaterial depth:0 = (
    if sourceMaterial == undefined or depth > 12 then return undefined
    local className = safeClassName sourceMaterial
    local lowerClass = toLower className

    if matchPattern lowerClass pattern:"*multi*material*" or className == "Multimaterial" do (
        local subCount = 0
        try (subCount = sourceMaterial.numsubs) catch()
        if subCount <= 0 do try (subCount = sourceMaterial.materialList.count) catch()
        if subCount > 0 do (
            local convertedMulti = multimaterial numsubs:subCount
            try (convertedMulti.name = sourceMaterial.name + "_COMPASS") catch()
            for index = 1 to subCount do (
                local child = undefined
                try (child = sourceMaterial[index]) catch()
                if child == undefined do try (child = sourceMaterial.materialList[index]) catch()
                local convertedChild = convertMaterialForExport child depth:(depth + 1)
                if convertedChild == undefined do convertedChild = standardMaterial name:("COMPASS_MATERIAL_" + index as string)
                try (convertedMulti[index] = convertedChild) catch()
                try (convertedMulti.materialIDList[index] = sourceMaterial.materialIDList[index]) catch()
            )
            return convertedMulti
        )
    )

    local result = standardMaterial()
    local exportName = "COMPASS_MATERIAL"
    try (exportName = sourceMaterial.name + "_COMPASS") catch()
    try (result.name = exportName) catch()
    try (result.diffuse = firstMaterialColor sourceMaterial) catch()
    try (result.ambient = result.diffuse * 0.2) catch()
    try (result.specularLevel = 20) catch()
    try (result.glossiness = 20) catch()

    local sourceBitmap = findDiffuseBitmap sourceMaterial
    local exportBitmap = makeFbxBitmap sourceBitmap
    -- Keep the success and failure branches as separate statements.
    -- This avoids the Max 2020 parser ambiguity previously reported at
    -- the `) else (` boundary in batch mode.
    if exportBitmap != undefined do (
        try (result.diffuseMap = exportBitmap) catch()
        try (result.diffuseMapEnable = true) catch()
        try (showTextureMap result exportBitmap true) catch()
        local sourcePath = normalizedTexturePath sourceBitmap
        if sourcePath != "" do (
            append COMPASS_TEXTURE_RECORDS #(exportName, sourcePath)
            format "COMPASS_ENGINE: Texture mapped | material=% | path=%\n" exportName sourcePath
        )
    )
    if exportBitmap == undefined do (
        format "COMPASS_ENGINE: No diffuse texture found | material=% | class=%\n" exportName className
    )

    local opacityValue = safeGetProperty sourceMaterial #opacity undefined
    if opacityValue != undefined do (
        try (
            if opacityValue <= 1.0 then result.opacity = opacityValue * 100.0 else result.opacity = opacityValue
        ) catch()
    )
    result
)

fn nodeFaceCount nodeValue = (
    local count = 0
    try (count = polyop.getNumFaces nodeValue) catch()
    if count <= 0 do try (count = getNumFaces nodeValue) catch()
    count
)

fn makeMeshNodeFromSnapshot sourceNode = (
    local result = undefined
    local meshValue = undefined
    try (meshValue = snapshotAsMesh sourceNode) catch()
    if meshValue != undefined do (
        try (
            result = mesh mesh:meshValue name:(sourceNode.name + "_COMPASS_EXPORT")
            result.transform = sourceNode.transform
            try (result.material = convertMaterialForExport sourceNode.material) catch()
        ) catch (
            result = undefined
        )
    )
    result
)

fn makeConvertedCopy sourceNode = (
    local result = undefined
    try (
        result = copy sourceNode
        result.name = sourceNode.name + "_COMPASS_EXPORT"
        result.transform = sourceNode.transform
        try (result.material = convertMaterialForExport sourceNode.material) catch()
        try (convertToMesh result) catch()
        if nodeFaceCount result <= 0 do (
            try (convertToPoly result) catch()
        )
        if nodeFaceCount result <= 0 do (
            delete result
            result = undefined
        )
    ) catch (
        if result != undefined do try (delete result) catch()
        result = undefined
    )
    result
)

fn buildExportGeometry sourceNodes = (
    local exportNodes = #()
    for sourceNode in sourceNodes do (
        local exported = makeMeshNodeFromSnapshot sourceNode
        if exported == undefined do exported = makeConvertedCopy sourceNode
        if exported == undefined do (
            try (exported = snapshot sourceNode) catch()
            if exported != undefined and nodeFaceCount exported <= 0 do (
                try (delete exported) catch()
                exported = undefined
            )
        )
        if exported != undefined do append exportNodes exported
    )
    exportNodes
)

fn configureFbx = (
    try (FBXExporterSetParam "ASCII" false) catch()
    try (FBXExporterSetParam "Animation" false) catch()
    try (FBXExporterSetParam "Cameras" false) catch()
    try (FBXExporterSetParam "Lights" false) catch()
    try (FBXExporterSetParam "EmbedTextures" true) catch()
    try (FBXExporterSetParam "SmoothingGroups" true) catch()
    try (FBXExporterSetParam "TangentsandBinormals" true) catch()
    try (FBXExporterSetParam "Preserveinstances" true) catch()
)

try (
    format "COMPASS_ENGINE: worker script started\n"
    local jobPath = undefined
    -- Desktop fallback bootstrap: global value set before this file is loaded.
    try (
        if COMPASS_JOB_PATH != undefined do jobPath = COMPASS_JOB_PATH
    ) catch()
    -- Batch path: value supplied through -mxsString.
    try (
        local opts = maxOps.mxsCmdLineArgs
        if opts != undefined do (
            try (jobPath = opts[#jobPath]) catch()
            if jobPath == undefined do try (jobPath = opts["jobPath"]) catch()
        )
    ) catch()
    -- Silent desktop fallback: value supplied through environment.
    if jobPath == undefined or jobPath == "" do (
        try (jobPath = sysInfo.getEnvVariable "COMPASS_JOB_PATH") catch()
    )
    if jobPath == undefined or jobPath == "" then throw "jobPath argument is missing"

    local jobText = readAllText jobPath
    local sourceMax = getJsonString jobText "source_max"
    local outputFbx = getJsonString jobText "output_fbx"
    local reportJson = getJsonString jobText "report_json"
    local textureManifest = getJsonString jobText "texture_manifest"
    if sourceMax == undefined or outputFbx == undefined or reportJson == undefined or textureManifest == undefined then throw "Invalid job JSON"
    COMPASS_TEXTURE_RECORDS = #()

    format "COMPASS_ENGINE: Loading %\n" sourceMax
    if not loadMaxFile sourceMax useFileUnits:true quiet:true then throw ("Could not load scene: " + sourceMax)

    local geo = for o in objects where (
        try ((superClassOf o == GeometryClass) and (not o.isHidden)) catch false
    ) collect o
    local matClasses = collectMaterialClasses()
    local hints = collectRendererHints matClasses
    local missingCount = 0
    try (missingCount = (AssetManager.GetAssets missingOnly:true).count) catch()
    writeReport reportJson sourceMax matClasses hints geo.count missingCount

    if geo.count == 0 then throw "No visible geometry found"

    -- Export evaluated mesh snapshots rather than renderer/proxy/group wrapper nodes.
    -- Some vehicle assets report as geometry in Max but become FBX nulls, which Blender
    -- imports as an EMPTY. Snapshotting produces actual mesh payloads for the FBX exporter.
    local exportGeo = buildExportGeometry geo
    if exportGeo.count == 0 then throw "No exportable mesh could be evaluated from scene geometry"
    writeTextureManifest textureManifest COMPASS_TEXTURE_RECORDS
    format "COMPASS_ENGINE: Prepared % evaluated mesh nodes with FBX-safe materials (texture recovery p4, records=%)\n" exportGeo.count COMPASS_TEXTURE_RECORDS.count
    select exportGeo
    configureFbx()
    exportFile outputFbx #noPrompt selectedOnly:true using:FBXEXP
    if not doesFileExist outputFbx then throw "FBX export failed"
    format "COMPASS_ENGINE: FBX created at %\n" outputFbx
    quitMax #noPrompt exitCode:0
) catch (
    format "COMPASS_ENGINE_ERROR: %\n" (getCurrentException())
    quitMax #noPrompt exitCode:1
)
