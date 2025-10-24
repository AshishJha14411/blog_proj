"use client"
import CreatePostForm from "@/components/common/CreatePostForm";
import { useAuth } from "@/hooks/useAuth"; 


export default function CreatePostPage () {
    const {  isAuthenticated  } = useAuth();
    console.log(isAuthenticated)
    return (
        <main>
            {isAuthenticated ? <CreatePostForm />:<p className="w-[60vw] h-[90vh] text-4xl mx-[35vw] mt-[20%]">Kindly Login to Access Create Stories</p>}
        </main>
    )
}