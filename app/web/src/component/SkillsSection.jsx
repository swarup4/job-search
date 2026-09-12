"use client";

import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useFormik } from "formik";
import { Layers, Plus } from "lucide-react";
import { Panel, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Dialog, DialogBody, DialogFooter } from "@/component/ui/dialog";
import { Field, Input } from "@/component/ui/field";
import { Button } from "@/component/ui/button";
import { Badge } from "@/component/ui/badge";
import {
    selectSkillCount,
    selectSkillGroups,
    skillAdded,
    skillGroupAdded,
    skillRemoved,
} from "@/store/profile/profileSlice";
import { skillGroupInitialValues, skillGroupSchema } from "@/util/schema";
import { cn } from "@/util/helper";

export function SkillsSection() {
    const groups = useSelector(selectSkillGroups);
    const total = useSelector(selectSkillCount);
    const dispatch = useDispatch();
    const [addingGroup, setAddingGroup] = useState(false);

    function commitGroup({ name }) {
        dispatch(skillGroupAdded(name.trim()));
        setAddingGroup(false);
    }

    return (
        <Panel>
            <PanelHeader>
                <Layers className="size-[16px] text-primary" />
                <PanelTitle>Skills</PanelTitle>
                <Badge variant="soft">{total}</Badge>
                <span className="grow" />
                <span className="text-[12.5px] text-muted-foreground">
                    grouped as in your .tex template
                </span>
                <button
                    type="button"
                    onClick={() => setAddingGroup(true)}
                    className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
                >
                    <Plus className="size-[14px]" />
                    Group
                </button>
            </PanelHeader>

            <div>
                {groups.length === 0 ? (
                    <p className="px-5 py-6 text-[13.5px] text-muted-foreground">
                        No skill groups yet. Add one to start listing skills.
                    </p>
                ) : (
                    groups.map((g, i) => (
                        <div
                            key={g.name}
                            className={cn(
                                "flex flex-wrap items-start gap-x-5 gap-y-3 px-5 py-4",
                                i < groups.length - 1 && "border-b border-border"
                            )}
                        >
                            <p className="w-[118px] shrink-0 pt-1 text-[13px] font-medium">{g.name}</p>
                            <div className="flex flex-wrap gap-2">
                                {g.items.map((s) => (
                                    <span
                                        key={s}
                                        className="inline-flex items-center gap-2 rounded-sm bg-primary-tint px-2.5 py-1.5 text-[13px] text-accent-foreground"
                                    >
                                        {s}
                                        <button
                                            type="button"
                                            aria-label={`Remove ${s}`}
                                            onClick={() =>
                                                dispatch(skillRemoved({ group: g.name, item: s }))
                                            }
                                            className="cursor-pointer text-[15px] leading-none opacity-45 hover:opacity-100"
                                        >
                                            ×
                                        </button>
                                    </span>
                                ))}
                                <SkillInput
                                    onAdd={(item) => dispatch(skillAdded({ group: g.name, item }))}
                                />
                            </div>
                        </div>
                    ))
                )}
            </div>

            {addingGroup ? (
                <Dialog
                    open
                    onClose={() => setAddingGroup(false)}
                    title="Add skill group"
                    description="Groups match the section names in your .tex template."
                >
                    <SkillGroupForm
                        taken={groups.map((g) => g.name)}
                        onSave={commitGroup}
                        onCancel={() => setAddingGroup(false)}
                    />
                </Dialog>
            ) : null}
        </Panel>
    );
}

/** Inline chip that becomes a text field — adding a skill is not worth a dialog. */
function SkillInput({ onAdd }) {
    const [value, setValue] = useState(null);

    function commit() {
        const item = (value ?? "").trim();
        if (item) onAdd(item);
        setValue(null);
    }

    if (value === null) {
        return (
            <button
                type="button"
                onClick={() => setValue("")}
                className="inline-flex cursor-pointer items-center rounded-sm border border-dashed border-border px-2.5 py-1.5 text-[13px] text-muted-foreground hover:border-primary hover:text-primary"
            >
                + add
            </button>
        );
    }

    return (
        <input
            autoFocus
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    commit();
                } else if (e.key === "Escape") {
                    setValue(null);
                }
            }}
            placeholder="Skill"
            className="h-[31px] w-[128px] rounded-sm border border-input bg-card px-2.5 text-[13px] outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
        />
    );
}

function SkillGroupForm({ taken, onSave, onCancel }) {
    const formik = useFormik({
        initialValues: skillGroupInitialValues,
        validationSchema: skillGroupSchema(taken),
        onSubmit: onSave,
    });

    const error = formik.touched.name && formik.errors.name;

    return (
        <form onSubmit={formik.handleSubmit} noValidate>
            <DialogBody>
                <Field label="Group name" error={error}>
                    <Input
                        autoFocus
                        placeholder="Languages"
                        invalid={Boolean(error)}
                        {...formik.getFieldProps("name")}
                    />
                </Field>
            </DialogBody>

            <DialogFooter>
                <Button type="button" variant="outline" size="sm" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit" size="sm">
                    Add group
                </Button>
            </DialogFooter>
        </form>
    );
}
