using UnrealBuildTool;
using System.Collections.Generic;

public class UnrealPlatformPrototypeEditorTarget : TargetRules
{
    public UnrealPlatformPrototypeEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("UnrealPlatformPrototype");
    }
}
