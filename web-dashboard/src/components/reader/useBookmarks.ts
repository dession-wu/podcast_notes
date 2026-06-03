"use client";

import { useState, useEffect } from "react";

export interface Bookmark {
  id: string;
  fileId: string;
  sectionId: string;
  paragraphIndex: number;
  preview: string;
  createdAt: number;
}

const STORAGE_KEY = "reader-bookmarks";

function loadBookmarks(): Bookmark[] {
  if (typeof window === "undefined") return [];
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved);
  } catch {
    // ignore
  }
  return [];
}

function saveBookmarks(bookmarks: Bookmark[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(bookmarks));
  } catch {
    // ignore
  }
}

export function useBookmarks(fileId: string) {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);

  useEffect(() => {
    setBookmarks(loadBookmarks().filter((b) => b.fileId === fileId));
  }, [fileId]);

  const addBookmark = (
    sectionId: string,
    paragraphIndex: number,
    preview: string
  ) => {
    const allBookmarks = loadBookmarks();
    const newBookmark: Bookmark = {
      id: `${fileId}-${sectionId}-${Date.now()}`,
      fileId,
      sectionId,
      paragraphIndex,
      preview: preview.slice(0, 80) + (preview.length > 80 ? "..." : ""),
      createdAt: Date.now(),
    };
    allBookmarks.push(newBookmark);
    saveBookmarks(allBookmarks);
    setBookmarks(allBookmarks.filter((b) => b.fileId === fileId));
    return newBookmark;
  };

  const removeBookmark = (bookmarkId: string) => {
    const allBookmarks = loadBookmarks().filter((b) => b.id !== bookmarkId);
    saveBookmarks(allBookmarks);
    setBookmarks(allBookmarks.filter((b) => b.fileId === fileId));
  };

  const toggleBookmark = (
    sectionId: string,
    paragraphIndex: number,
    preview: string
  ) => {
    const existing = bookmarks.find(
      (b) => b.sectionId === sectionId && b.paragraphIndex === paragraphIndex
    );
    if (existing) {
      removeBookmark(existing.id);
      return false;
    } else {
      addBookmark(sectionId, paragraphIndex, preview);
      return true;
    }
  };

  const isBookmarked = (sectionId: string, paragraphIndex: number) => {
    return bookmarks.some(
      (b) => b.sectionId === sectionId && b.paragraphIndex === paragraphIndex
    );
  };

  return {
    bookmarks,
    addBookmark,
    removeBookmark,
    toggleBookmark,
    isBookmarked,
  };
}
