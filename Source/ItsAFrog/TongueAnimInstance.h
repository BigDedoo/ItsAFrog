// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "TongueAnimInstance.generated.h"

/** A complete, game-thread-authored snapshot consumed by the tongue Anim Blueprint. */
USTRUCT(BlueprintType)
struct ITSAFROG_API FTonguePoseData
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	FTransform RootGuide = FTransform::Identity;

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	FTransform MidAGuide = FTransform::Identity;

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	FTransform MidBGuide = FTransform::Identity;

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	FTransform TipGuide = FTransform::Identity;

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	bool bTongueActive = false;

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	float ExtensionAlpha = 0.0f;
};

/**
 * Native base class for the small tongue Animation Blueprint.
 *
 * The public guide transforms are in TongueMesh component space. SplineTransforms
 * contains per-bone component-space offsets for Spline IK's Control Points pin.
 */
UCLASS(BlueprintType)
class ITSAFROG_API UTongueAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	/** High-level guides intended for debugging and optional Anim Blueprint use. */
	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	FTransform RootGuide = FTransform::Identity;

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	FTransform MidAGuide = FTransform::Identity;

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	FTransform MidBGuide = FTransform::Identity;

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	FTransform TipGuide = FTransform::Identity;

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	bool bTongueActive = false;

	UPROPERTY(BlueprintReadOnly, Category="Tongue")
	float TongueExtensionAlpha = 0.0f;

	/**
	 * Dynamic offsets to connect to Spline IK's Control Points array.
	 * Leave Spline IK bAutoCalculateSpline enabled so this has one entry per bone.
	 */
	UPROPERTY(BlueprintReadOnly, Category="Tongue|Spline")
	TArray<FTransform> SplineTransforms;

	/** Publishes one coherent pose snapshot from the owning character. */
	UFUNCTION(BlueprintCallable, Category="Tongue")
	void SetTonguePose(const FTonguePoseData& InPose);

protected:
	virtual void NativeInitializeAnimation() override;
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;

private:
	void CacheReferenceChain();
	void BuildSplineControlPointOffsets();
	static FVector EvaluateGuidePosition(const FTonguePoseData& Pose, float Alpha);
	static FQuat EvaluateGuideRotation(const FTonguePoseData& Pose, float Alpha);

	// SetTonguePose and NativeUpdateAnimation both execute on the game thread. The
	// Anim Graph only sees the public fields after NativeUpdateAnimation has copied
	// this complete plain-data snapshot, so worker-thread evaluation never touches
	// the frog actor or skeletal mesh component.
	FTonguePoseData PendingPose;

	TArray<int32> ReferenceChainBoneIndices;
	TArray<FTransform> ReferenceChainTransforms;
	bool bReferenceChainCached = false;
};
