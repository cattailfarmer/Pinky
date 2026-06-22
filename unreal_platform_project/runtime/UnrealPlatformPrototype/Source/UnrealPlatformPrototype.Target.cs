using UnrealBuildTool;
using System.Collections.Generic;

public class UnrealPlatformPrototypeTarget : TargetRules
{
    public UnrealPlatformPrototypeTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("UnrealPlatformPrototype");
    }
}
