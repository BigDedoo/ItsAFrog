// Fill out your copyright notice in the Description page of Project Settings.

#include "TongueAnimInstance.h"

#include "Algo/Reverse.h"
#include "AnimationRuntime.h"
#include "Engine/SkeletalMesh.h"
#include "Components/SkeletalMeshComponent.h"

void UTongueAnimInstance::SetTonguePose(const FTonguePoseData& InPose)
{
	PendingPose = InPose;
}

void UTongueAnimInstance::NativeInitializeAnimation()
{
	Super::NativeInitializeAnimation();
	CacheReferenceChain();
}

void UTongueAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
	Super::NativeUpdateAnimation(DeltaSeconds);

	if (!bReferenceChainCached)
	{
		CacheReferenceChain();
	}

	// This is the game-thread handoff point. All fields are copied before the
	// Anim Graph is evaluated, while worker threads only read the public snapshot.
	RootGuide = PendingPose.RootGuide;
	MidAGuide = PendingPose.MidAGuide;
	MidBGuide = PendingPose.MidBGuide;
	TipGuide = PendingPose.TipGuide;
	bTongueActive = PendingPose.bTongueActive;
	TongueExtensionAlpha = PendingPose.ExtensionAlpha;

	BuildSplineControlPointOffsets();
}

void UTongueAnimInstance::CacheReferenceChain()
{
	ReferenceChainBoneIndices.Reset();
	ReferenceChainTransforms.Reset();
	bReferenceChainCached = false;

	USkeletalMeshComponent* SkeletalMeshComponent = GetSkelMeshComponent();
	USkeletalMesh* SkeletalMesh = SkeletalMeshComponent ? SkeletalMeshComponent->GetSkeletalMeshAsset() : nullptr;
	if (!SkeletalMesh)
	{
		return;
	}

	const FReferenceSkeleton& RefSkeleton = SkeletalMesh->GetRefSkeleton();
	int32 BoneIndex = RefSkeleton.FindBoneIndex(TEXT("Bone_001"));
	const int32 StartBoneIndex = RefSkeleton.FindBoneIndex(TEXT("Bone_000"));
	if (BoneIndex == INDEX_NONE || StartBoneIndex == INDEX_NONE)
	{
		UE_LOG(LogTemp, Warning, TEXT("UTongueAnimInstance requires Bone_000 and Bone_001 in the tongue Skeleton."));
		return;
	}

	while (BoneIndex != INDEX_NONE)
	{
		ReferenceChainBoneIndices.Add(BoneIndex);
		if (BoneIndex == StartBoneIndex)
		{
			break;
		}
		BoneIndex = RefSkeleton.GetParentIndex(BoneIndex);
	}

	if (ReferenceChainBoneIndices.Last() != StartBoneIndex)
	{
		UE_LOG(LogTemp, Warning, TEXT("Bone_001 is not a descendant of Bone_000 in the tongue Skeleton."));
		ReferenceChainBoneIndices.Reset();
		return;
	}

	Algo::Reverse(ReferenceChainBoneIndices);

	TArray<FTransform> ComponentSpaceTransforms;
	FAnimationRuntime::FillUpComponentSpaceTransforms(RefSkeleton, RefSkeleton.GetRefBonePose(), ComponentSpaceTransforms);
	ReferenceChainTransforms.Reserve(ReferenceChainBoneIndices.Num());
	for (const int32 ChainBoneIndex : ReferenceChainBoneIndices)
	{
		ReferenceChainTransforms.Add(ComponentSpaceTransforms[ChainBoneIndex]);
	}

	SplineTransforms.SetNum(ReferenceChainBoneIndices.Num());
	bReferenceChainCached = ReferenceChainBoneIndices.Num() >= 2;
}

FVector UTongueAnimInstance::EvaluateGuidePosition(const FTonguePoseData& Pose, float Alpha)
{
	const FVector Positions[] = {
		Pose.RootGuide.GetLocation(),
		Pose.MidAGuide.GetLocation(),
		Pose.MidBGuide.GetLocation(),
		Pose.TipGuide.GetLocation()
	};

	const float ScaledAlpha = FMath::Clamp(Alpha, 0.0f, 1.0f) * 3.0f;
	const int32 Segment = FMath::Min(FMath::FloorToInt(ScaledAlpha), 2);
	const float SegmentAlpha = ScaledAlpha - static_cast<float>(Segment);
	const FVector& P0 = Positions[Segment];
	const FVector& P1 = Positions[Segment + 1];
	const FVector T0 = Segment == 0 ? P1 - P0 : (Positions[Segment + 1] - Positions[Segment - 1]) * 0.5f;
	const FVector T1 = Segment == 2 ? P1 - Positions[Segment - 1] : (Positions[Segment + 2] - P0) * 0.5f;
	return FMath::CubicInterp(P0, T0, P1, T1, SegmentAlpha);
}

FQuat UTongueAnimInstance::EvaluateGuideRotation(const FTonguePoseData& Pose, float Alpha)
{
	const FQuat Rotations[] = {
		Pose.RootGuide.GetRotation(),
		Pose.MidAGuide.GetRotation(),
		Pose.MidBGuide.GetRotation(),
		Pose.TipGuide.GetRotation()
	};

	const float ScaledAlpha = FMath::Clamp(Alpha, 0.0f, 1.0f) * 3.0f;
	const int32 Segment = FMath::Min(FMath::FloorToInt(ScaledAlpha), 2);
	const float SegmentAlpha = ScaledAlpha - static_cast<float>(Segment);
	return FQuat::Slerp(Rotations[Segment], Rotations[Segment + 1], SegmentAlpha).GetNormalized();
}

void UTongueAnimInstance::BuildSplineControlPointOffsets()
{
	if (!bReferenceChainCached)
	{
		return;
	}

	const int32 BoneCount = ReferenceChainTransforms.Num();
	for (int32 BoneIndex = 0; BoneIndex < BoneCount; ++BoneIndex)
	{
		const float Alpha = static_cast<float>(BoneIndex) / static_cast<float>(BoneCount - 1);
		const FTransform DesiredTransform(EvaluateGuideRotation(PendingPose, Alpha), EvaluateGuidePosition(PendingPose, Alpha));
		const FTransform& ReferenceTransform = ReferenceChainTransforms[BoneIndex];

		FTransform& ControlPoint = SplineTransforms[BoneIndex];
		ControlPoint.SetLocation(DesiredTransform.GetLocation() - ReferenceTransform.GetLocation());
		ControlPoint.SetRotation(DesiredTransform.GetRotation() * ReferenceTransform.GetRotation().Inverse());
		ControlPoint.SetScale3D(FVector::OneVector);
	}
}
